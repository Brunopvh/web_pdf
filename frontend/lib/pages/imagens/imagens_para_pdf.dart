import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'package:web_pdf/pages/urls.dart';
import 'package:archive/archive.dart';
import 'dart:html' as html;

class ImagenToPdfPage extends StatefulWidget {
  const ImagenToPdfPage({super.key});

  @override
  State<ImagenToPdfPage> createState() => _ImagenToPdfPageState();
}

class _ImagenToPdfPageState extends State<ImagenToPdfPage> {
  List<PlatformFile> selectedFiles = [];
  bool filesReady = false;
  bool isProcessing = false;
  double progress = 0.0;
  bool canDownload = false;
  String exportFilename = "imagens_para_pdf.zip";
  List<List<int>> pdfFiles = [];
  
  // 1. Variável para armazenar o ID da tarefa
  String? _taskId; 

  Future<void> _pickFiles() async {
    setState(() {
      progress = 0.0;
      isProcessing = false;
      canDownload = false;
      _taskId = null; // Reseta o ID da tarefa
      filesReady = false;
      pdfFiles.clear();
    });

    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['png', 'jpg', 'jpeg'],
      allowMultiple: true,
      withData: true,
    );

    if (result != null) {
      selectedFiles = result.files;
      bool allHaveBytes = selectedFiles.every((f) => f.bytes != null);
      setState(() {
        filesReady = allHaveBytes && selectedFiles.isNotEmpty;
      });
    }
  }

  Future<void> _processFiles() async {
    if (!filesReady) return;

    setState(() {
      progress = 0.0;
      isProcessing = true;
      canDownload = false;
      _taskId = null; // Garante que está nulo antes de iniciar
    });

    Map<String, dynamic> JSON_IP = await readJsonLocalAsset();
    String IP_SERVER = JSON_IP["ip_server"];
    String RT_IMG = JSON_IP["rt_imgs_to_pdf"];
    String URL_SERVER = '$IP_SERVER/$RT_IMG';
    var uri = Uri.parse(URL_SERVER);
    var request = http.MultipartRequest("POST", uri);

    for (final file in selectedFiles) {
      if (file.bytes != null) {
        request.files.add(
          http.MultipartFile.fromBytes("files", file.bytes!, filename: file.name),
        );
      }
    }

    // 2. Envia a requisição e captura a resposta para obter o task_id
    var streamedResponse = await request.send();
    var response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      var data = jsonDecode(response.body);
      
      // Captura o task_id da resposta (assumindo que a chave é 'task_id')
      String? receivedTaskId = data["task_id"]; 

      if (receivedTaskId == null) {
         // Trata erro se o servidor não retornar o ID (opcional)
         ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Erro no servidor: ID da tarefa não recebido.")),
         );
         setState(() { isProcessing = false; });
         return;
      }
      
      setState(() {
        _taskId = receivedTaskId;
      });
      
      // Inicia monitoramento do progresso
      Timer.periodic(const Duration(milliseconds: 700), (timer) async {
        
        // 3. Usa o task_id na URL de polling
        var progressUri = Uri.parse('$IP_SERVER/progress/$_taskId');
        
        try {
            var resp = await http.get(progressUri);
            if (resp.statusCode == 200) {
              var data = jsonDecode(resp.body);
              
              // O progresso no Flutter é 0.0 a 1.0, mas seu servidor retorna 0 a 100.
              // Vamos dividir por 100 para o Flutter.
              double newProgress = (data["progress"] ?? 0) / 100.0; 

              setState(() {
                progress = newProgress;
              });

              if (data["done"] == true) {
                timer.cancel();
                setState(() {
                  isProcessing = false;
                  canDownload = true;
                });
              }
            } else if (resp.statusCode == 404) {
                 // Trata caso a tarefa não seja encontrada durante o polling
                 timer.cancel();
                 setState(() { isProcessing = false; progress = 0.0; });
            }
        } catch (e) {
            timer.cancel();
            print("Erro no polling: $e");
            setState(() { isProcessing = false; });
        }
      });
    } else {
      // Lida com erro na requisição POST inicial
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Erro ao iniciar processamento: ${response.statusCode}")),
      );
      setState(() { isProcessing = false; });
    }
  }

  Future<void> _downloadFile() async {
    if (_taskId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Erro: ID da tarefa não encontrado.")),
      );
      return;
    }
    
    Map<String, dynamic> JSON_IP = await readJsonLocalAsset();
    String IP_SERVER = JSON_IP["ip_server"];
    
    // 4. Usa o task_id como parâmetro de query (query parameter)
    // Constrói a URL: /download?task_id={ID}
    //var downloadUri = Uri.parse('$IP_SERVER/download').replace(
    //  queryParameters: {'task_id': _taskId!}
    //);
    var downloadUri = Uri.parse('$IP_SERVER/download/$_taskId');

    var resp = await http.get(downloadUri);
    
    if (resp.statusCode == 200) {
      final blob = html.Blob([resp.bodyBytes], 'application/zip');
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..setAttribute("download", exportFilename)
        ..click();
        
      // Limpa o ID após o download bem-sucedido
      setState(() { _taskId = null; });
      
    } else {
      // Exibe mensagem de erro (ex: 400 Arquivo não pronto)
      var errorData = jsonDecode(resp.body);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Erro no download: ${errorData['error'] ?? resp.statusCode}")),
      );
    }
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Imagens para PDF"), centerTitle: true),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Barra de progresso (sempre visível)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              children: [
                LinearProgressIndicator(
                  // Usar um valor entre 0.0 e 1.0 para a barra
                  value: isProcessing ? null : progress,
                  backgroundColor: Colors.grey[300],
                  color: Colors.green,
                  minHeight: 8,
                ),
                const SizedBox(height: 20),
                Text(
                  // Exibir o progresso como porcentagem (0 a 100)
                  "Progresso: ${(progress * 100).toInt()}%",
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
          const SizedBox(height: 30),
          Wrap(
            spacing: 20,
            runSpacing: 20,
            alignment: WrapAlignment.center,
            children: [
              ElevatedButton.icon(
                onPressed: _pickFiles,
                icon: const Icon(Icons.image),
                label: const Text("Selecionar Imagens"),
              ),
              ElevatedButton.icon(
                onPressed: filesReady && !isProcessing ? _processFiles : null,
                icon: const Icon(Icons.picture_as_pdf),
                label: const Text("Converter"),
              ),
              ElevatedButton.icon(
                onPressed: canDownload ? _downloadFile : null,
                icon: const Icon(Icons.download),
                label: const Text("Baixar Resultado"),
              ),
            ],
          ),
        ],
      ),
    );
  }
}