import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';

class JoinPdfsPage extends StatefulWidget {
  const JoinPdfsPage({super.key});

  @override
  State<JoinPdfsPage> createState() => _JoinPdfsPageState();
}

class _JoinPdfsPageState extends State<JoinPdfsPage> {
  List<String> selectedFiles = [];
  double progress = 0.0;
  bool isProcessing = false;
  bool canDownload = false;

  Future<void> _pickFiles() async {
    setState(() {
      progress = 0.0;
      isProcessing = true;
      canDownload = false;
    });

    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
      allowMultiple: true,
    );

    if (result != null) {
      selectedFiles = result.paths.whereType<String>().toList();

      // Simula progresso de upload
      for (int i = 1; i <= 10; i++) {
        await Future.delayed(const Duration(milliseconds: 100));
        setState(() {
          progress = i / 10;
        });
      }
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

    // Simula processamento
    for (int i = 1; i <= 20; i++) {
      await Future.delayed(const Duration(milliseconds: 100));
      setState(() {
        progress = i / 20;
      });
    }

    setState(() {
      isProcessing = false;
      canDownload = true;
    });
  }

  Future<void> _downloadFile() async {
    if (!canDownload) return;

    setState(() {
      progress = 0.0;
      isProcessing = true;
    });

    // Simula download
    for (int i = 1; i <= 15; i++) {
      await Future.delayed(const Duration(milliseconds: 100));
      setState(() {
        progress = i / 15;
      });
    }

    setState(() {
      isProcessing = false;
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
              height: 80,
              width: 80,
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

          // Botões de ação
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

          // Lista de arquivos selecionados
          if (selectedFiles.isNotEmpty)
            Expanded(
              child: ListView.builder(
                itemCount: selectedFiles.length,
                itemBuilder: (context, index) {
                  return ListTile(
                    leading: const Icon(Icons.picture_as_pdf),
                    title: Text(
                      selectedFiles[index].split('/').last,
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
