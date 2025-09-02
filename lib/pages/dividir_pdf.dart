import 'dart:html' as html; // só funciona na Web
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'package:web_pdf/pages/urls.dart';

//final String BACKEND_URL = "http://127.0.0.1:5000/uploads/pdfs";

class SplitPdfsPage extends StatefulWidget {
  const SplitPdfsPage({super.key});

  @override
  State<SplitPdfsPage> createState() => _SplitPdfsPageState();
}

class _SplitPdfsPageState extends State<SplitPdfsPage> {
  PlatformFile? selectedFile;
  double progress = 0.0;
  bool isProcessing = false;
  bool canDownload = false;
  bool fileReady = false;
  String? downloadUrl;

  Future<void> _pickFile() async {
    setState(() {
      progress = 0.0;
      isProcessing = false;
      canDownload = false;
      downloadUrl = null;
      fileReady = false;
    });

    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
      allowMultiple: false, // apenas 1 PDF
      withData: true,
    );

    if (result != null && result.files.single.bytes != null) {
      setState(() {
        selectedFile = result.files.single;
        fileReady = true;
      });
    }
  }

  Future<void> _processFile() async {
    if (!fileReady || selectedFile?.bytes == null) return;

    setState(() {
      progress = 0.0;
      isProcessing = true;
      canDownload = false;
    });

    var uri = Uri.parse("$BACKEND_URL/split");
    var request = http.MultipartRequest('POST', uri);
    print('Enviando arquivos..');
    request.files.add(
      http.MultipartFile.fromBytes(
        'files',
        selectedFile!.bytes!,
        filename: selectedFile!.name,
      ),
    );
    print('Aguardando resposta...');
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

    for (int i = 1; i <= 15; i++) {
      await Future.delayed(const Duration(milliseconds: 80));
      setState(() {
        progress = i / 15;
      });
    }

    final anchor =
        html.AnchorElement(href: downloadUrl)
          ..setAttribute("download", "paginas_divididas.zip")
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
      appBar: AppBar(title: const Text("Dividir PDF"), centerTitle: true),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Barra de progresso circular
          Padding(
            padding: const EdgeInsets.all(20),
            child: SizedBox(
              height: 90,
              width: 90,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  CircularProgressIndicator(
                    value: isProcessing ? null : progress,
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
                onPressed: _pickFile,
                icon: const Icon(Icons.upload_file),
                label: const Text("Selecionar PDF"),
              ),
              ElevatedButton.icon(
                onPressed: fileReady && !isProcessing ? _processFile : null,
                icon: const Icon(Icons.call_split),
                label: const Text("Dividir"),
              ),
              ElevatedButton.icon(
                onPressed: canDownload ? _downloadFile : null,
                icon: const Icon(Icons.download),
                label: const Text("Baixar ZIP"),
              ),
            ],
          ),

          const SizedBox(height: 30),

          if (selectedFile != null)
            Padding(
              padding: const EdgeInsets.all(10),
              child: ListTile(
                leading: const Icon(Icons.picture_as_pdf),
                title: Text(
                  selectedFile!.name,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
        ],
      ),
    );
  }
}
