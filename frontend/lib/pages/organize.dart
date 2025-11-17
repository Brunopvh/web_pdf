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

class OrganizePage extends StatefulWidget {
  const OrganizePage({super.key});

  @override
  State<OrganizePage> createState() => _OrganizePageState();
}

class _OrganizePageState extends State<OrganizePage> {
  List<PlatformFile> pdfFiles = [];
  List<PlatformFile> imageFiles = [];
  PlatformFile? xlsxFile;
  bool isProcessing = false;
  double progress = 0.0;
  final TextEditingController patternController = TextEditingController();
  final TextEditingController columnController = TextEditingController(); // NOVO

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

  // 🔹 LIMPAR TODOS OS ARQUIVOS E CAMPOS
  void clearAllFiles() {
    setState(() {
      pdfFiles.clear();
      imageFiles.clear();
      xlsxFile = null;
      patternController.clear();
      columnController.clear();
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('🧹 Todos os arquivos e campos foram limpos.')),
    );
  }

  // Enviar arquivos para o servidor
  Future<void> processFiles() async {
    if (pdfFiles.isEmpty && imageFiles.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selecione pelo menos um PDF ou imagem')),
      );
      return;
    }

    if (xlsxFile != null && columnController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Digite o nome da coluna no Excel antes de enviar.')),
      );
      return;
    }

    if (xlsxFile == null && patternController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Digite o digite um texto/busca na caixa apropriada!')),
      );
      return;
    }

    setState(() {
      isProcessing = true;
      progress = 0.0;
    });

    try {
      Map<String, dynamic> jsonIp = await readJsonLocalAsset();
      String ipServer = jsonIp["ip_server"];
      String rtProcessDocs = jsonIp["rt_process_docs"];

      final hasSheet = xlsxFile != null;
      Uri uriToSend = hasSheet
          ? Uri.parse('$ipServer/${jsonIp["rt_process_docs"]}')
          : Uri.parse('$ipServer/${jsonIp["rt_process_pattern"]}');

      var request = http.MultipartRequest("POST", uriToSend);

      // PARA PDFS
      final listPdfsJson = <Map<String, dynamic>>[];
      for (final file in pdfFiles) {
        final bytes = kIsWeb ? file.bytes! : await File(file.path!).readAsBytes();
        listPdfsJson.add({
          "filename": file.name,
          "bytes_base64": base64Encode(bytes),
        });
      }

      // PARA IMAGENS
      final listImagesJson = <Map<String, dynamic>>[];
      for (final file in imageFiles) {
        final bytes = kIsWeb ? file.bytes! : await File(file.path!).readAsBytes();
        listImagesJson.add({
          "filename": file.name,
          "bytes_base64": base64Encode(bytes),
        });
      }

      // Inserir planilha e nome da coluna dentro do JSON
      String? sheetBase64;
      if (xlsxFile != null) {
        final bytes = kIsWeb ? xlsxFile!.bytes! : await File(xlsxFile!.path!).readAsBytes();
        sheetBase64 = base64Encode(bytes);
      }

      // JSON FINAL
      final payload = {
        "text": patternController.text,
        "list_pdfs": listPdfsJson,
        "list_images": listImagesJson,
        "sheet": sheetBase64 ?? "",     // sempre enviado
        "column_text": columnController.text, // sempre enviado
      };

      // ENVIAR AO SERVER
      final response = await http.post(
        uriToSend,
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(payload),
      );

      if (response.statusCode == 200) {
        final bytes = response.bodyBytes;

        if (bytes.isEmpty) {
          throw Exception("Resposta do servidor vazia.");
        }

        // Nome padrão, caso o servidor não envie
        String filename = "resultado_filtrado.zip";
        final contentDisposition = response.headers["content-disposition"];
        if (contentDisposition != null) {
          final match = RegExp(r'filename="?(.+)"?').firstMatch(contentDisposition);
          if (match != null && match.group(1) != null) {
            filename = match.group(1)!;
          }
        }

        // WEB
        if (kIsWeb) {
          final blob = html.Blob([bytes]);
          final url = html.Url.createObjectUrlFromBlob(blob);

          final anchor = html.document.createElement('a') as html.AnchorElement
            ..href = url
            ..style.display = 'none'
            ..download = filename;

          html.document.body?.children.add(anchor);
          anchor.click();
          html.document.body?.children.remove(anchor);
          html.Url.revokeObjectUrl(url);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('✅ Download de "$filename" iniciado.')),
          );
        }
        // ANDROID / DESKTOP
        else {
          final outputPath = p.join(Directory.systemTemp.path, filename);
          await File(outputPath).writeAsBytes(bytes, flush: true);

          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('✅ Arquivo salvo em: $outputPath')),
          );
        }
      } else {
        String errorMessage =
      '❌ Erro (${response.statusCode}): Servidor retornou um erro inesperado.';

        try {
          final jsonResponse = jsonDecode(response.body);
          errorMessage =
              '❌ Erro (${response.statusCode}): ${jsonResponse["error"] ?? "Erro desconhecido"}';
        } catch (_) {
          // Se não for JSON, mantém a mensagem padrão
        }

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(errorMessage)),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('⚠️ Erro de conexão ou processamento: $e')),
      );
    } finally {
      setState(() {
        isProcessing = false;
        progress = 1.0;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
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
            Card(
              margin: const EdgeInsets.symmetric(vertical: 8),
              elevation: 3,
              child: ListTile(
                leading: const Icon(Icons.picture_as_pdf, color: Colors.red),
                title: const Text('Adicionar PDFs'),
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
                title: const Text('Adicionar Imagens'),
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
                title: const Text('Carregar Planilha XLSX'),
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
            TextField(
              controller: patternController,
              decoration: const InputDecoration(
                labelText: 'Padrão de texto (opcional)',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.text_fields),
              ),
            ),
            const SizedBox(height: 30),
            ElevatedButton.icon(
              onPressed: isProcessing ? null : processFiles,
              icon: const Icon(Icons.play_circle_fill),
              label: const Text('Processar Documentos'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.teal,
                minimumSize: const Size(double.infinity, 50),
              ),
            ),
            const SizedBox(height: 20),
            if (isProcessing)
              Column(
                children: [
                  const Text('Processando...'),
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
