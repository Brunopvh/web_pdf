import 'package:flutter/services.dart' show rootBundle;
import 'dart:convert'; // Importe para decodificar JSON

Future<String> loadAsset(String asset) async {
  //return await rootBundle.loadString('assets/data/seu_arquivo.json');
  return await rootBundle.loadString(asset);
}

Future<Map<String, dynamic>> readJsonLocalAsset({String file='assets/data/ips.json'}) async {
  String jsonString = await loadAsset(file);
  final Map<String, dynamic> jsonMap = json.decode(jsonString);
  return jsonMap;
}

