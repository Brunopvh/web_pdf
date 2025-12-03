import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'package:web_pdf/pages/urls.dart';
import 'package:archive/archive.dart';
import 'dart:html' as html;

class DocumentsToSheetPage extends StatefulWidget {
  const DocumentsToSheetPage({super.key});

  @override
  State<DocumentsToSheetPage> createState() => _DocumentsToSheetPageState();
}

class _DocumentsToSheetPageState extends State<DocumentsToSheetPage> {
  List<PlatformFile> selectedFiles = [];
  bool filesReady = false;
  bool isProcessing = false;
  double progress = 0.0;
  bool canDownload = false;
  String exportFilename = "documentos.zip";
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
      allowedExtensions: ['.pdf', '.png', '.jpg', '.jpeg'],
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

  // ============== MÉTODO: MONITORAR PROGRESSO ==============
  Future<void> _pollProgress(String ipServer, String taskId) async {
    // Cria um Timer periódico (por exemplo, a cada 900ms)
    Timer.periodic(const Duration(milliseconds: 900), (timer) async {
      var progressUri = Uri.parse('$ipServer/progress/$taskId');

      try {
        var resp = await http.get(progressUri);
        if (resp.statusCode == 200) {
          var data = jsonDecode(resp.body);

          double newProgress = (data["progress"] ?? 0) / 100.0;

          if (mounted) {
            // Garante que o widget ainda está ativo
            setState(() {
              progress = newProgress;
            });
          }

          if (data["done"] == true) {
            timer.cancel(); // 🛑 Importante: Para o timer!
            if (mounted) {
              setState(() {
                isProcessing = false;
                canDownload = true;
                // Mantemos o _taskId para o download
              });
            }
          }
        } else {
          // Se der 404 (tarefa expirada) ou outro erro
          timer.cancel();
          if (mounted) {
            setState(() {
              isProcessing = false;
              progress = 0.0;
            });
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(
                  "Erro no monitoramento: Status ${resp.statusCode}",
                ),
              ),
            );
          }
        }
      } catch (e) {
        timer.cancel();
        print("Erro no polling: $e");
        if (mounted) {
          setState(() {
            isProcessing = false;
          });
        }
      }
    });
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
    String RT_DOCS_TO_SHEET = JSON_IP["rt_docs_to_sheet"];
    String URL_SERVER = '$IP_SERVER/$RT_DOCS_TO_SHEET';
    var uri = Uri.parse(URL_SERVER);
    var request = http.MultipartRequest("POST", uri);
    for (final file in selectedFiles) {
      if (file.bytes != null) {
        request.files.add(
          http.MultipartFile.fromBytes(
            "files",
            file.bytes!,
            filename: file.name,
          ),
        );
      }
    }

    // Envia a requisição e captura a resposta para obter o task_id
    var streamedResponse = await request.send();
    var response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      var data = jsonDecode(response.body);

      // Captura o task_id da resposta (assumindo que a chave é 'task_id')
      String? receivedTaskId = data["task_id"];

      if (receivedTaskId == null) {
        // Trata erro se o servidor não retornar o ID (opcional)
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Erro no servidor: ID da tarefa não recebido."),
          ),
        );
        setState(() {
          isProcessing = false;
        });
        return;
      }

      setState(() {
        _taskId = receivedTaskId;
      });
      // Inicia monitoramento do progresso
      this._pollProgress(IP_SERVER, receivedTaskId);
    } else {
      // Lida com erro na requisição POST inicial
      String errorMessage = "Erro ao iniciar processamento: ${response.statusCode}";
      dynamic errorData = "-";
      try {
        // Tenta decodificar o erro do backend (JSONResponse do FastAPI)
        errorData = jsonDecode(response.body);
        errorMessage =
            "Erro ao iniciar processamento: ${errorData['error'] ?? response.statusCode}";
      } catch (_) {}

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            "Status: ${response.statusCode} - ${errorMessage}",
          ),
        ),
      );
      setState(() {
        isProcessing = false;
      });
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

    var downloadUri = Uri.parse('$IP_SERVER/download/$_taskId');
    var resp = await http.get(downloadUri);

    if (resp.statusCode == 200) {
      final blob = html.Blob([resp.bodyBytes,], 'application/zip');
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor =
          html.AnchorElement(href: url)
            ..setAttribute("download", this.exportFilename)
            ..click();

      // Limpa o ID após o download bem-sucedido
      //setState(() { _taskId = null; });
    } else {
      // Exibe mensagem de erro (ex: 400 Arquivo não pronto)
      var errorData = jsonDecode(resp.body);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            "Erro no download: ${errorData['error'] ?? resp.statusCode}",
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Documentos para planilha"),
        centerTitle: true,
      ),
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
                label: const Text("Selecionar Documentos"),
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
