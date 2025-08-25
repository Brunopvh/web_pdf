import 'dart:html' as html; // só funciona na Web
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;

final String BACKEND_URL = "http://localhost:5000/uploads/pdfs";

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
  bool filesReady = false; // <- controle novo
  String? downloadUrl;

  //******************************************
  // URL do seu backend em Python
  final String backendUrl = BACKEND_URL; // ajuste aqui

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
      allowedExtensions: ['pdf'],
      allowMultiple: true,
      withData: true, // importante p/ web (pega os bytes)
    );

    if (result != null) {
      selectedFiles = result.files;

      // Verifica se todos têm bytes carregados
      bool allHaveBytes = selectedFiles.every((f) => f.bytes != null);

      setState(() {
        filesReady = allHaveBytes && selectedFiles.isNotEmpty;
      });
    }
  }

  Future<void> _processFiles() async {
    if (!filesReady) return; // segurança extra

    setState(() {
      progress = 0.0;
      isProcessing = true;
      canDownload = false;
    });

    var uri = Uri.parse("$backendUrl/join");
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
        SnackBar(
          content: Text(
            "Erro no processamento: ${streamedResponse.statusCode}",
          ),
        ),
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

    final anchor =
        html.AnchorElement(href: downloadUrl)
          ..setAttribute("download", "resultado.pdf")
          ..click();

    setState(() {
      isProcessing = false;
      progress = 1.0;
    });

    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text("Download concluído!")));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Juntar PDFs"), centerTitle: true),
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
                    value:
                        isProcessing ? null : progress, // null = indeterminado
                    strokeWidth: 8,
                  ),
                  Center(
                    child: Text(
                      (!isProcessing && progress > 0)
                          ? "${(progress * 100).toInt()}%"
                          : "",
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
                onPressed:
                    filesReady && !isProcessing
                        ? _processFiles
                        : null, // só habilita quando tudo estiver pronto
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
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 20),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey.shade300),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Scrollbar(
                  thumbVisibility: true,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(10),
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
              ),
            ),
        ],
      ),
    );
  }
}
