# QGIS用pythonスクリプト
# split_railroad_geojson.py で分割したgeojsonを統合

from pathlib import Path

basepath = Path('')
splited_path = basepath / 'splited'

features = []
for i in range(594):
  layer = iface.addVectorLayer(str(splited_path / f'{i}.geojson'), '', 'ogr')
  geoms = QgsGeometry.fromWkt('GEOMETRYCOLLECTION EMPTY')
  for feature in layer.getFeatures():
    geoms = geoms.combine(feature.geometry())

  feature = layer.getFeature(0)
  feature.clearGeometry()
  feature.setGeometry(geoms)
  QgsProject.instance().removeMapLayer(layer.id())
  features.append(feature)

geojson = QgsJsonExporter().exportFeatures(features)

(basepath / 'modified.geojson').write_text(geojson, encoding='utf-8')
