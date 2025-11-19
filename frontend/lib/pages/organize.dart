import 'dart:io';
import 'dart:typed_data';
import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:file_picker/file_picker.dart';
import 'package:path/path.dart' as p;
import 'package:web_pdf/pages/urls.dart';
import 'package:universal_html/html.dart' as html;

import 'dart:async'; // Importado para usar Timer
import 'package:web_pdf/pages/urls.dart';


class OrganizePage extends StatefulWidget {
  const OrganizePage({super.key});

  @override
  State<OrganizePage> createState() => _OrganizePageState();
}

class _OrganizePageState extends State<OrganizePage> {
  // Variáveis de seleção de arquivos
  List<PlatformFile> pdfFiles = [];
  List<PlatformFile> imageFiles = [];
  PlatformFile? xlsxFile;
  
  // Variáveis de estado e controle
  bool isProcessing = false;
  double progress = 0.0;
  bool canDownload = false; // NOVO: Controla se o download está pronto
  String exportFilename = 'resultado_filtrado.zip';
  String? _taskId; // NOVO: Armazena o ID da tarefa para polling e download

  // Controladores de texto
  final TextEditingController patternController = TextEditingController();
  final TextEditingController columnController = TextEditingController();

  // ... (pickPdfFiles, pickImageFiles, pickXlsxFile permanecem inalterados) ...

  // 🔹 LIMPAR TODOS OS ARQUIVOS E CAMPOS
  void clearAllFiles() {
    setState(() {
      pdfFiles.clear();
      imageFiles.clear();
      xlsxFile = null;
      patternController.clear();
      columnController.clear();
      
      // Limpa os estados de processamento
      isProcessing = false;
      progress = 0.0;
      canDownload = false;
      _taskId = null;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('🧹 Todos os arquivos e campos foram limpos.')),
    );
  }

  // ============== NOVO MÉTODO: MONITORAR PROGRESSO ==============
  Future<void> _pollProgress(String ipServer, String taskId) async {
    Timer.periodic(const Duration(milliseconds: 700), (timer) async {
      var progressUri = Uri.parse('$ipServer/progress/$taskId');
      
      try {
        var resp = await http.get(progressUri);
        
        if (resp.statusCode == 200) {
          var data = jsonDecode(resp.body);
          
          double newProgress = (data["progress"] ?? 0) / 100.0; 

          setState(() {
            progress = newProgress;
          });

          if (data["done"] == true) {
            timer.cancel();
            setState(() {
              isProcessing = false;
              canDownload = true;
              // O arquivo real do ZIP está pronto, o download pode ser iniciado.
            });
          }
        } else {
           // Se der 404 (tarefa expirada) ou outro erro
           timer.cancel();
           setState(() { isProcessing = false; progress = 0.0; });
           ScaffoldMessenger.of(context).showSnackBar(
             SnackBar(content: Text("Erro no monitoramento: Status ${resp.statusCode}")),
           );
        }
      } catch (e) {
        timer.cancel();
        print("Erro no polling: $e");
        setState(() { isProcessing = false; });
      }
    });
  }

  // ============== NOVO MÉTODO: DOWNLOAD DO ARQUIVO ZIP ==============
  Future<void> _downloadFile() async {
    if (_taskId == null || !canDownload) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Aguarde o processamento ou ID da tarefa ausente.")),
      );
      return;
    }
    
    Map<String, dynamic> jsonIp = await readJsonLocalAsset();
    String ipServer = jsonIp["ip_server"];
    
    // Constrói a URL usando o Path Parameter /download/{task_id}
    var downloadUri = Uri.parse('$ipServer/download/$_taskId'); 

    // O header 'content-disposition' será usado pelo servidor para definir o nome.
    var resp = await http.get(downloadUri);
    
    if (resp.statusCode == 200) {
      if (kIsWeb) {
        // Lógica de download para Web
        final blob = html.Blob([resp.bodyBytes], 'application/zip');
        final url = html.Url.createObjectUrlFromBlob(blob);
        
        // Define o nome do arquivo usando a variável de estado
        final anchor = html.AnchorElement(href: url)
          ..setAttribute("download", exportFilename) 
          ..click();
          
        html.Url.revokeObjectUrl(url); // Limpa a URL do blob
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('✅ Download de "$exportFilename" iniciado.')),
        );
      } else {
         // (Para Desktop/Mobile, o FilePicker não fornece a lógica de download automático)
         // Você precisará de uma biblioteca como `path_provider` e `permission_handler`
         // para salvar em um diretório específico fora do web.
         ScaffoldMessenger.of(context).showSnackBar(
           const SnackBar(content: Text('Download não implementado para esta plataforma.')),
         );
      }
      
      // Limpa o estado após download bem-sucedido
      setState(() { 
        _taskId = null;
        canDownload = false;
        progress = 0.0;
      });
      
    } else {
      // Exibe mensagem de erro do servidor
      String errorMessage = "Erro no download (Status: ${resp.statusCode}).";
      try {
        var errorData = jsonDecode(resp.body);
        errorMessage = "❌ Erro: ${errorData['error'] ?? 'Erro desconhecido'}";
      } catch (_) {}
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(errorMessage)),
      );
    }
  }

  // ============== MÉTODO ATUALIZADO: processFiles ==============
  Future<void> processFiles() async {
    // ... (Validações de hasSheet e patternController permanecem inalteradas) ...
    if (pdfFiles.isEmpty && imageFiles.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selecione pelo menos um PDF ou imagem')),
      );
      return;
    }

    final hasSheet = xlsxFile != null;
    if (hasSheet && columnController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Digite o nome da coluna no Excel antes de enviar.')),
      );
      return;
    }
    if (!hasSheet && patternController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Digite o digite um texto/busca na caixa apropriada!')),
      );
      return;
    }


    setState(() {
      isProcessing = true;
      progress = 0.0;
      canDownload = false;
      _taskId = null;
    });

    try {
      Map<String, dynamic> jsonIp = await readJsonLocalAsset();
      String ipServer = jsonIp["ip_server"];

      final uri = hasSheet
          ? Uri.parse('$ipServer/${jsonIp["rt_process_docs"]}')
          : Uri.parse('$ipServer/${jsonIp["rt_process_pattern"]}');

      var request = http.MultipartRequest("POST", uri);
      
      // ... (Adicionar PDFs, imagens, XLSX, fields de column_name e pattern permanecem inalterados) ...
      
      // Adicionar PDFs e imagens
      for (final file in [...pdfFiles, ...imageFiles]) {
        if (kIsWeb) {
          request.files.add(http.MultipartFile.fromBytes(
            file.extension == "pdf" ? 'pdfs' : 'images',
            file.bytes!,
            filename: file.name,
          ));
        } else {
          request.files.add(await http.MultipartFile.fromPath(
            file.extension == "pdf" ? 'pdfs' : 'images',
            file.path!,
          ));
        }
      }

      // XLSX ou padrão
      if (xlsxFile != null) {
        if (kIsWeb) {
          request.files.add(http.MultipartFile.fromBytes(
              'file_sheet', xlsxFile!.bytes!,
              filename: xlsxFile!.name));
        } else {
          request.files
              .add(await http.MultipartFile.fromPath('file_sheet', xlsxFile!.path!));
        }
      }

      // Envia o nome da coluna associada à planilha
      request.fields['column_name'] = columnController.text;
      // Envia o padrão textual caso não haja planilha
      if (!hasSheet) {
        request.fields['pattern'] = patternController.text;
      }
      
      // Envia requisição e aguarda a resposta que contém o task_id
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);


      if (response.statusCode == 200) {
        // A resposta DEVE ser o JSON contendo o task_id
        final jsonResponse = jsonDecode(response.body);
        
        String? receivedTaskId = jsonResponse['task_id'];
        
        if (receivedTaskId != null) {
          // 1. Armazena o ID
          setState(() {
            _taskId = receivedTaskId;
          });
          // 2. Inicia o monitoramento de progresso
          _pollProgress(ipServer, receivedTaskId);
        } else {
          throw Exception("ID da tarefa não recebido do servidor.");
        }
        
      } else {
        // ... (Tratamento de erro) ...
        String errorMessage =
            '❌ Erro (${response.statusCode}): Servidor retornou um erro inesperado.';

        try {
          final jsonResponse = jsonDecode(response.body);
          errorMessage =
              '❌ Erro (${response.statusCode}): ${jsonResponse['error'] ?? 'Erro desconhecido'}';
        } catch (_) {}

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(errorMessage)),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('⚠️ Erro de conexão ou processamento: $e')),
      );
    } finally {
      // isProcessing será definido como false pelo _pollProgress
      // Apenas garantimos que, se houver falha, ele pare de processar.
      if (_taskId == null) {
        setState(() {
          isProcessing = false;
        });
      }
    }
  }

  // Selecionar PDFs
  Future<void> pickPdfFiles() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: true,
      type: FileType.custom,
      allowedExtensions: ['pdf'],
    );
    if (result != null) {
      setState(() {
        pdfFiles = result.files;
      });
    }
  }

  // Selecionar imagens
  Future<void> pickImageFiles() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: true,
      type: FileType.image,
    );
    if (result != null) {
      setState(() {
        imageFiles = result.files;
      });
    }
  }

  // Selecionar planilha XLSX
  Future<void> pickXlsxFile() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: false,
      type: FileType.custom,
      allowedExtensions: ['xlsx'],
    );
    if (result != null && result.files.isNotEmpty) {
      setState(() {
        xlsxFile = result.files.single;
      });
    }
  }


  @override
  Widget build(BuildContext context) {
    // ... (restante do código build) ...
    return Scaffold(
      appBar: AppBar(
        title: const Text('Organizar Documentos'),
        backgroundColor: Colors.blueGrey.shade700,
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_forever),
            tooltip: 'Limpar tudo',
            onPressed: clearAllFiles,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // ... (Cards de seleção de arquivos permanecem inalterados) ...
            Card(
              margin: const EdgeInsets.symmetric(vertical: 8),
              elevation: 3,
              child: ListTile(
                leading: const Icon(Icons.picture_as_pdf, color: Colors.red),
                title: Text('Adicionar PDFs (${pdfFiles.length} arquivos)'),
                trailing: ElevatedButton(
                  onPressed: pickPdfFiles,
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                  child: const Text('Selecionar'),
                ),
              ),
            ),
            Card(
              margin: const EdgeInsets.symmetric(vertical: 8),
              elevation: 3,
              child: ListTile(
                leading: const Icon(Icons.image, color: Colors.blue),
                title: Text('Adicionar Imagens (${imageFiles.length} arquivos)'),
                trailing: ElevatedButton(
                  onPressed: pickImageFiles,
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.blue),
                  child: const Text('Selecionar'),
                ),
              ),
            ),
            Card(
              margin: const EdgeInsets.symmetric(vertical: 8),
              elevation: 3,
              child: ListTile(
                leading: const Icon(Icons.table_chart, color: Colors.green),
                title: Text('Carregar Planilha XLSX ${xlsxFile != null ? "(1 arquivo)" : ""}'),
                trailing: ElevatedButton(
                  onPressed: pickXlsxFile,
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                  child: const Text('Selecionar'),
                ),
              ),
            ),
            if (xlsxFile != null)
              Padding(
                padding: const EdgeInsets.only(top: 12.0),
                child: TextField(
                  controller: columnController,
                  decoration: const InputDecoration(
                    labelText: 'Nome da coluna Excel para filtrar os textos',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.table_chart),
                  ),
                ),
              ),
            const SizedBox(height: 20),
            // Se o XLSX não foi selecionado, o padrão de texto é necessário.
            if (xlsxFile == null)
              TextField(
                controller: patternController,
                decoration: const InputDecoration(
                  labelText: 'Padrão de texto para busca obrigatório',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.text_fields),
                ),
              ),
            const SizedBox(height: 30),
            
            // Botão Processar
            ElevatedButton.icon(
              onPressed: isProcessing ? null : processFiles,
              icon: const Icon(Icons.play_circle_fill),
              label: const Text('Processar Documentos'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.teal,
                minimumSize: const Size(double.infinity, 50),
              ),
            ),
            
            // NOVO: Botão de Download (visível apenas após o processamento, 
            // se o backend usasse task_id e polling).
            if (canDownload) ...[
                const SizedBox(height: 20),
                ElevatedButton.icon(
                  onPressed: _downloadFile,
                  icon: const Icon(Icons.download),
                  label: const Text('Baixar Resultado'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.deepOrange,
                    minimumSize: const Size(double.infinity, 50),
                  ),
                ),
            ],

            const SizedBox(height: 20),
            if (isProcessing)
              Column(
                children: [
                  Text('Processando: ${(progress * 100).toInt()}%'),
                  const SizedBox(height: 10),
                  LinearProgressIndicator(value: progress),
                ],
              ),
          ],
        ),
      ),
    );
  }
}