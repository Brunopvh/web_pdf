import 'package:flutter/material.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final buttonsOptions = [
      "Organizar Documentos",
      "Aplicar OCR",
      "Para Excel",
      "Juntar PDFs",
      "Dividir PDFs",
      "PDF para Imagens",
      "Imagens para PDF",
    ];

    return Scaffold(
      appBar: AppBar(title: const Text("Página Inicial"), centerTitle: true),
      body: Center(
        child: GridView.builder(
          padding: const EdgeInsets.all(20),
          gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
            maxCrossAxisExtent: 180, // largura máxima de cada botão
            crossAxisSpacing: 20,
            mainAxisSpacing: 20,
          ),
          itemCount: buttonsOptions.length,
          itemBuilder: (context, index) {
            final option = buttonsOptions[index];
            return ElevatedButton(
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.all(11),
                //fixedSize: const Size(50, 30),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              onPressed: () {
                if (option == "Juntar PDFs") {
                  Navigator.pushNamed(context, '/joinPdfs');
                } else if (option == "Dividir PDFs") {
                  Navigator.pushNamed(context, '/splitPdfs');
                } else if (option == "PDF para Imagens") {
                  Navigator.pushNamed(context, '/pdfToImages');
                } else if (option == "Aplicar OCR") {
                  Navigator.pushNamed(context, '/ocr');
                } else if (option == "Imagens para PDF") {
                  Navigator.pushNamed(context, '/imgToPdf');
                } else if (option == "Organizar Documentos") {
                  Navigator.pushNamed(context, '/organizar');
;
                }

                // As outras opções ficam sem ação por enquanto
              },
              child: Text(
                option,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 16),
              ),
            );
          },
        ),
      ),
    );
  }
}
