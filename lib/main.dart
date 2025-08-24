import 'package:flutter/material.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'App TCC',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const HomePage(),
      routes: {
        '/joinPdfs': (context) => const JoinPdfsPage(),
      },
    );
  }
}

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final options = [
      "Organizar PDFs",
      "Aplicar OCR",
      "Para Excel",
      "Juntar PDFs",
      "Dividir PDFs",
      "PDF para Imagens",
      "Imagens para PDF",
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text("Página Inicial"),
        centerTitle: true,
      ),
      body: Center(
        child: GridView.builder(
          padding: const EdgeInsets.all(20),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2, // duas colunas
            crossAxisSpacing: 20,
            mainAxisSpacing: 20,
          ),
          itemCount: options.length,
          itemBuilder: (context, index) {
            final option = options[index];
            return ElevatedButton(
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.all(20),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              onPressed: () {
                if (option == "Juntar PDFs") {
                  Navigator.pushNamed(context, '/joinPdfs');
                }
                // As outras opções ficam sem ação por enquanto
              },
              child: Text(
                option,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 18),
              ),
            );
          },
        ),
      ),
    );
  }
}

class JoinPdfsPage extends StatelessWidget {
  const JoinPdfsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Juntar PDFs"),
      ),
      body: const Center(
        child: Text(
          "Aqui ficará a funcionalidade de juntar PDFs",
          style: TextStyle(fontSize: 20),
        ),
      ),
    );
  }
}
