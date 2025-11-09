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
  String? downloadUrl;
  String exportFilename = "imagens_para_pdf.zip";
  List<List<int>> pdfFiles = []; // PDFs retornados pelo servidor

  Future<void> _pickFiles() async {
    setState(() {
      progress = 0.0;
      isProcessing = false;
      canDownload = false;
      downloadUrl = null;
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
      pdfFiles.clear();
    });

    Map<String, dynamic> JSON_IP = await readJsonLocalAsset();
    String IP_SERVER = JSON_IP["ip_server"];
    String RT_IMGS_TO_PDF = JSON_IP["rt_imgs_to_pdf"]; // rota no seu servidor
    String URL_SERVER = "$IP_SERVER/$RT_IMGS_TO_PDF";

    bool processingError = false;

    for (int i = 0; i < selectedFiles.length; i++) {
      final file = selectedFiles[i];
      if (file.bytes != null) {
        var uri = Uri.parse(URL_SERVER);
        var request = http.MultipartRequest("POST", uri);

        // Enviar lista, mas só com UM arquivo
        request.files.add(http.MultipartFile.fromBytes(
          "files",
          file.bytes!,
          filename: file.name,
        ));

        try {
          var response = await request.send();
          if (response.statusCode == 200) {
            final rawBytes = await response.stream.toBytes();

            // Esperando que o servidor retorne diretamente um PDF (ou ZIP com 1 PDF)
            // Aqui tentamos decodificar ZIP também, para compatibilidade
            try {
              final archive = ZipDecoder().decodeBytes(rawBytes);
              for (final f in archive) {
                if (f.isFile && f.name.toLowerCase().endsWith(".pdf")) {
                  pdfFiles.add(f.content as List<int>);
                }
              }
            } catch (_) {
              // Caso não seja ZIP, tratamos como PDF único
              pdfFiles.add(rawBytes);
            }

            setState(() {
              progress = (i + 1) / selectedFiles.length;
            });
          } else {
            processingError = true;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text("Erro no processamento da imagem ${i + 1}: ${response.statusCode}")),
            );
            break;
          }
        } catch (e) {
          processingError = true;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text("Erro ao enviar a imagem ${i + 1}: $e")),
          );
          break;
        }
      }
    }

    setState(() {
      isProcessing = false;
    });

    if (!processingError && pdfFiles.isNotEmpty) {
      final archive = Archive();
      for (int i = 0; i < pdfFiles.length; i++) {
        final filename = "documento${i + 1}.pdf";
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
        const SnackBar(content: Text("Nenhum arquivo foi convertido.")),
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
                  value: isProcessing ? null : progress,
                  backgroundColor: Colors.grey[300],
                  color: Colors.green,
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
