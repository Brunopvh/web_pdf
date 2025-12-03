import 'package:flutter/material.dart';
import 'package:web_pdf/pages/home_page.dart';
import 'package:web_pdf/pages/pdfs/juntar_pdf.dart';
import 'package:web_pdf/pages/pdfs/dividir_pdf.dart';
import 'package:web_pdf/pages/pdfs/pdfs_para_img.dart';
import 'package:web_pdf/pages/ocr/image_ocr.dart';
import 'package:web_pdf/pages/imagens/imagens_para_pdf.dart';
import 'package:web_pdf/pages/organize.dart';
import 'package:web_pdf/pages/excel/excel.dart';

// Versão Web
void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Conversor de Documentos',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const HomePage(),
      routes: {
          '/joinPdfs': (context) => const JoinPdfsPage(),
          '/splitPdfs': (context) => const SplitPdfsPage(),
          '/pdfToImages': (context) => const ConvertPdfsPage(),
          '/ocr': (context) => const OcrPage(), 
          '/imgToPdf': (context) => const ImagenToPdfPage(),
          '/organizar': (context) => const OrganizePage(),
          '/docsToSheet': (context) => const DocumentsToSheetPage(),
        },
    );
  }
}

