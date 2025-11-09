import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'package:web_pdf/pages/urls.dart';
import 'package:archive/archive.dart';  // Importando para manipular arquivos ZIP
import 'dart:html' as html; // Adicione esta linha


class OcrPage extends StatefulWidget {
  const OcrPage({super.key});

  @override
  State<OcrPage> createState() => _OcrPageState();
}

class _OcrPageState extends State<OcrPage> {
  List<PlatformFile> selectedFiles = [];
  bool filesReady = false;
  bool isProcessing = false;
  double progress = 0.0;
  bool canDownload = false;
  String? downloadUrl;
  String exportFilename = "resultado_ocr.zip";
  List<List<int>> pdfFiles = [];  // Lista para armazenar os arquivos PDF extraídos

  Future<void> _pickFiles() async {
    setState(() {
      progress = 0.0;
      isProcessing = false;
      canDownload = false;
      downloadUrl = null;
      filesReady = false;
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
    });

    Map<String, dynamic> JSON_IP = await readJsonLocalAsset();
    String IP_SERVER = JSON_IP["ip_server"];
    String RT_OCR = JSON_IP["rt_ocr"];
    String URL_SERVER = "$IP_SERVER/$RT_OCR";

    bool processingError = false;

    for (int i = 0; i < selectedFiles.length; i++) {
      final file = selectedFiles[i];
      if (file.bytes != null) {
        var uri = Uri.parse(URL_SERVER);
        var request = http.MultipartRequest("POST", uri);
        request.files.add(http.MultipartFile.fromBytes(
          "files",
          file.bytes!,
          filename: file.name,
        ));

        try {
          var response = await request.send();
          if (response.statusCode == 200) {
            final rawBytes = await response.stream.toBytes();
            // Descompactando o arquivo ZIP recebido
            final archive = ZipDecoder().decodeBytes(rawBytes);
            
            // Armazenando o conteúdo extraído (esperando que seja um único arquivo PDF dentro)
            int pdfIndex = 1;
            for (final file in archive) {
              if (file.isFile) {
                // Verifique se é um arquivo PDF e adicione à lista com nomes únicos
                pdfFiles.add(file.content as List<int>);

                setState(() {
                  progress = (i + 1) / selectedFiles.length;
                });
              }
              pdfIndex++;
            }
          } else {
            processingError = true;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text("Erro no processamento do arquivo ${i + 1}: ${response.statusCode}")),
            );
            break;
          }
        } catch (e) {
          processingError = true;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text("Erro ao enviar o arquivo ${i + 1}: $e")),
          );
          break;
        }
      }
    }

    setState(() {
      isProcessing = false;
    });

    // Gera o ZIP com os PDFs extraídos
    if (!processingError && pdfFiles.isNotEmpty) {
      final archive = Archive();
      for (int i = 0; i < pdfFiles.length; i++) {
        final filename = 'documento${i + 1}.pdf';
        final fileData = pdfFiles[i];

        archive.addFile(ArchiveFile(filename, fileData.length, fileData));
      }

      final zipEncoder = ZipEncoder();
      final zipData = zipEncoder.encode(archive)!;

      final blob = html.Blob(
        [Uint8List.fromList(zipData)],
        'application/zip',
      );
      final url = html.Url.createObjectUrlFromBlob(blob);

      setState(() {
        downloadUrl = url;
        canDownload = true;
        progress = 1.0;
      });
    } else if (!processingError) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Nenhum arquivo foi processado com sucesso.")),
      );
    }
  }

  Future<void> _downloadFile() async {
    if (downloadUrl == null) return;

    final anchor = html.AnchorElement(href: downloadUrl)
      ..setAttribute("download", exportFilename)
      ..click();

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Download concluído!")),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Aplicar OCR"), centerTitle: true),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Barra de progresso
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              children: [
                LinearProgressIndicator(
                  value: isProcessing ? null : progress, // Progresso gradual
                  backgroundColor: Colors.grey[300],
                  color: Colors.blue,
                  minHeight: 8,
                ),
                const SizedBox(height: 20),
                Text(
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
                icon: const Icon(Icons.text_snippet),
                label: const Text("Aplicar OCR"),
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
