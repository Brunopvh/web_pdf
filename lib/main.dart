import 'package:flutter/material.dart';
import 'package:web_pdf/pages/home_page.dart';
import 'package:web_pdf/pages/juntar_pdf.dart';

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
      routes: {'/joinPdfs': (context) => const JoinPdfsPage()},
    );
  }
}

