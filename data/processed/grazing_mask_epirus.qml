<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.34" styleCategories="AllStyleCategories" hasScaleBasedVisibilityFlag="0">
  <pipe>
    <provider>
      <resampling enabled="false" zoomedInResamplingMethod="nearestNeighbour" zoomedOutResamplingMethod="nearestNeighbour" maxOversampling="2"/>
    </provider>
    <rasterrenderer type="paletted" opacity="1" band="1" alphaBand="-1" nodataColor="">
      <colorPalette>
        <paletteEntry value="0" color="#e6e6e6" label="excluded" alpha="255"/>
        <paletteEntry value="1" color="#5fae3a" label="grassland" alpha="255"/>
        <paletteEntry value="2" color="#b8863b" label="shrubland" alpha="255"/>
        <paletteEntry value="3" color="#d9d0b0" label="sparse" alpha="255"/>
        <paletteEntry value="4" color="#f2e394" label="cropland" alpha="255"/>
      </colorPalette>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
    <huesaturation saturation="0" grayscaleMode="0" colorizeOn="0"/>
    <rasterresampler maxOversampling="2"/>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
