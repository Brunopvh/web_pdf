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

    await request.send();

    // iniciar monitoramento do progresso
    Timer.periodic(const Duration(milliseconds: 700), (timer) async {
      var resp = await http.get(Uri.parse("$IP_SERVER/progress"));
      if (resp.statusCode == 200) {
        var data = jsonDecode(resp.body);
        setState(() {
          progress = data["progress"];
        });

        if (data["done"] == true) {
          timer.cancel();
          setState(() {
            isProcessing = false;
            canDownload = true;
          });
        }
      }
    });
  }

  Future<void> _downloadFile() async {
    Map<String, dynamic> JSON_IP = await readJsonLocalAsset();
    String IP_SERVER = JSON_IP["ip_server"];

    var resp = await http.get(Uri.parse("$IP_SERVER/download"));
    if (resp.statusCode == 200) {
      final blob = html.Blob([resp.bodyBytes], 'application/zip');
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..setAttribute("download", exportFilename)
        ..click();
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
                  value: isProcessing ? null : progress,
                  backgroundColor: Colors.grey[300],
                  color: Colors.green,
                  minHeight: 8,
                ),
                const SizedBox(height: 20),
                Text(
                  "Progresso: ${(progress).toInt()}%",
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
