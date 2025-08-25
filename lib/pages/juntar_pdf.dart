import 'dart:html' as html; // só funciona na Web
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;

class JoinPdfsPage extends StatefulWidget {
  const JoinPdfsPage({super.key});

  @override
  State<JoinPdfsPage> createState() => _JoinPdfsPageState();
}

class _JoinPdfsPageState extends State<JoinPdfsPage> {
  List<PlatformFile> selectedFiles = [];
  double progress = 0.0;
  bool isProcessing = false;
  bool canDownload = false;
  String? downloadUrl;

  // URL do seu backend em Python
  final String backendUrl = "http://localhost:5000/uploads/pdfs"; // ajuste aqui

  Future<void> _pickFiles() async {
    setState(() {
      progress = 0.0;
      isProcessing = true;
      canDownload = false;
      downloadUrl = null;
    });

    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
      allowMultiple: true,
      withData: true, // importante p/ web (pega os bytes)
    );

    if (result != null) {
      selectedFiles = result.files;
    }

    setState(() {
      isProcessing = false;
    });
  }

  Future<void> _processFiles() async {
    if (selectedFiles.isEmpty) return;

    setState(() {
      progress = 0.0;
      isProcessing = true;
      canDownload = false;
    });

    var uri = Uri.parse("$backendUrl/join"); // endpoint Python
    var request = http.MultipartRequest('POST', uri);

    for (var file in selectedFiles) {
      if (file.bytes != null) {
        request.files.add(
          http.MultipartFile.fromBytes(
            'files',
            file.bytes!,
            filename: file.name,
          ),
        );
      }
    }

    var streamedResponse = await request.send();

    if (streamedResponse.statusCode == 200) {
      // Backend deve retornar o PDF processado diretamente
      var bytes = await streamedResponse.stream.toBytes();

      // Criar URL temporária para download
      final blob = html.Blob([bytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);

      setState(() {
        isProcessing = false;
        canDownload = true;
        downloadUrl = url;
        progress = 1.0;
      });
    } else {
      setState(() {
        isProcessing = false;
        progress = 0.0;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Erro no processamento: ${streamedResponse.statusCode}")),
      );
    }
  }

  Future<void> _downloadFile() async {
    if (downloadUrl == null) return;

    setState(() {
      progress = 0.0;
      isProcessing = true;
    });

    // Simula progresso de download
    for (int i = 1; i <= 15; i++) {
      await Future.delayed(const Duration(milliseconds: 80));
      setState(() {
        progress = i / 15;
      });
    }

    final anchor = html.AnchorElement(href: downloadUrl)
      ..setAttribute("download", "resultado.pdf")
      ..click();

    setState(() {
      isProcessing = false;
      progress = 1.0;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Download concluído!")),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Juntar PDFs"),
        centerTitle: true,
      ),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Barra de progresso circular fixa
          Padding(
            padding: const EdgeInsets.all(20),
            child: SizedBox(
              height: 90,
              width: 90,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  CircularProgressIndicator(
                    value: isProcessing ? progress : 0,
                    strokeWidth: 8,
                  ),
                  Center(
                    child: Text(
                      isProcessing ? "${(progress * 100).toInt()}%" : "0%",
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
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
                onPressed: _processFiles,
                icon: const Icon(Icons.merge_type),
                label: const Text("Processar"),
              ),
              ElevatedButton.icon(
                onPressed: canDownload ? _downloadFile : null,
                icon: const Icon(Icons.download),
                label: const Text("Baixar PDF"),
              ),
            ],
          ),

          const SizedBox(height: 30),

          if (selectedFiles.isNotEmpty)
            Expanded(
              child: ListView.builder(
                itemCount: selectedFiles.length,
                itemBuilder: (context, index) {
                  return ListTile(
                    leading: const Icon(Icons.picture_as_pdf),
                    title: Text(
                      selectedFiles[index].name,
                      overflow: TextOverflow.ellipsis,
                    ),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }
}
