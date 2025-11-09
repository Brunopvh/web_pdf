import 'dart:typed_data';
import 'dart:html' as html;
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'package:web_pdf/pages/urls.dart';
import 'package:archive/archive.dart'; // Para manipular ZIPs

class ConvertPdfsPage extends StatefulWidget {
  const ConvertPdfsPage({super.key});

  @override
  State<ConvertPdfsPage> createState() => _ConvertPdfsPageState();
}

class _ConvertPdfsPageState extends State<ConvertPdfsPage> {
  List<PlatformFile> selectedFiles = [];
  bool filesReady = false;
  bool isProcessing = false;
  double progress = 0.0;
  bool canDownload = false;
  String? downloadUrl;
  String exportFilename = "pdf-para-imagens.zip";
  List<List<int>> imageFiles = []; // Lista para armazenar os zips extraídos

  Future<void> _pickFiles() async {
    // Selecionar os arquivos
    setState(() {
      progress = 0.0;
      isProcessing = false;
      canDownload = false;
      downloadUrl = null;
      filesReady = false;
      imageFiles.clear();
    });

    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
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
      imageFiles.clear();
    });

    Map<String, dynamic> JSON_IP = await readJsonLocalAsset();
    String IP_SERVER = JSON_IP["ip_server"];
    String RT_CONVERT = JSON_IP["rt_convert_pdf"];
    String URL_SERVER = "$IP_SERVER/$RT_CONVERT";

    bool processingError = false;

    for (int i = 0; i < selectedFiles.length; i++) {
      final file = selectedFiles[i];
      if (file.bytes != null) {
        var uri = Uri.parse(URL_SERVER);
        var request = http.MultipartRequest("POST", uri);

        // Enviar só 1 arquivo por vez
        request.files.add(http.MultipartFile.fromBytes(
          "files",
          file.bytes!,
          filename: file.name,
        ));

        try {
          var response = await request.send();
          if (response.statusCode == 200) {
            final rawBytes = await response.stream.toBytes();

            // Descompactar o zip retornado pelo servidor
            final archive = ZipDecoder().decodeBytes(rawBytes);

            for (final fileInZip in archive) {
              if (fileInZip.isFile) {
                imageFiles.add(fileInZip.content as List<int>);
              }
            }

            setState(() {
              progress = (i + 1) / selectedFiles.length;
            });
          } else {
            processingError = true;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text("Erro no arquivo ${i + 1}: ${response.statusCode}")),
            );
            break;
          }
        } catch (e) {
          processingError = true;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text("Erro ao enviar arquivo ${i + 1}: $e")),
          );
          break;
        }
      }
    }

    setState(() {
      isProcessing = false;
    });

    // Gera o ZIP final com todas as imagens recebidas
    if (!processingError && imageFiles.isNotEmpty) {
      final archive = Archive();
      for (int i = 0; i < imageFiles.length; i++) {
        final filename = 'imagem_${i + 1}.png';
        final fileData = imageFiles[i];
        archive.addFile(ArchiveFile(filename, fileData.length, fileData));
      }

      final zipEncoder = ZipEncoder();
      final zipData = zipEncoder.encode(archive)!;

      final blob = html.Blob([Uint8List.fromList(zipData)], 'application/zip');
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
      appBar: AppBar(title: const Text("Converter PDFs"), centerTitle: true),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Barra de progresso SEMPRE visível
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              children: [
                LinearProgressIndicator(
                  value: isProcessing ? null : progress,
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
                icon: const Icon(Icons.upload_file),
                label: const Text("Selecionar PDFs"),
              ),
              ElevatedButton.icon(
                onPressed: filesReady && !isProcessing ? _processFiles : null,
                icon: const Icon(Icons.play_circle_fill),
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
