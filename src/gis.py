import whitebox
import rasterio
import geopandas as gpd
from typing import Dict, Tuple
import numpy as np

class CatchmentDelineator:
    """
    GIS-based catchment delineation using DEM
    (Section 3.1 from report - Table 1 characteristics)
    """
    
    def __init__(self, dem_path: str, output_dir: str):
        """
        Initialize with DEM file path
        
        Args:
            dem_path: Path to GeoTIFF DEM file
            output_dir: Directory for intermediate GIS outputs
        """
        self.wbt = whitebox.WhiteboxTools()
        self.wbt.set_working_directory(output_dir)
        self.dem_path = dem_path
        
    def preprocess_dem(self) -> str:
        """
        Preprocess DEM: Fill sinks and calculate flow direction
        """
        # Fill depressions
        filled_dem = 'filled_dem.tif'
        self.wbt.breach_depressions(self.dem_path, filled_dem)
        
        # Flow direction (D8)
        flow_dir = 'flow_direction.tif'
        self.wbt.d8_pointer(filled_dem, flow_dir)
        
        # Flow accumulation
        flow_acc = 'flow_accumulation.tif'
        self.wbt.flow_accumulation(flow_dir, flow_acc)
        
        return flow_acc
    
    def delineate_catchment(self, outlet_lat: float, 
                           outlet_lon: float) -> str:
        """
        Delineate catchment area from bridge coordinates
        
        Args:
            outlet_lat: Latitude of bridge site
            outlet_lon: Longitude of bridge site
            
        Returns:
            Path to catchment shapefile
        """
        # Preprocess first
        flow_acc = self.preprocess_dem()
        
        # Snap outlet to stream
        snapped_outlet = 'snapped_outlet.shp'
        self.wbt.vector_stream_extraction(flow_acc, snapped_outlet, 1000)
        
        # Delineate watershed
        catchment_shp = 'catchment.shp'
        self.wbt.watershed(self.dem_path, flow_acc, 
                          outlet_lat, outlet_lon, catchment_shp)
        
        return catchment_shp
    
    def calculate_catchment_properties(self, catchment_shp: str) -> Dict:
        """
        Calculate catchment characteristics (Table 1 from report)
        
        Returns:
            Dictionary with A, L, Lc, Hmax, Hmin, Slope
        """
        # Load catchment polygon
        gdf = gpd.read_file(catchment_shp)
        
        # Area (km²)
        area_km2 = gdf.geometry.area.iloc[0] / 1_000_000  # m² to km²
        
        # Extract stream network
        streams = 'streams.shp'
        self.wbt.extract_streams('flow_direction.tif', streams, 1000)
        
        # Load streams
        streams_gdf = gpd.read_file(streams)
        
        # Length of main stream (km)
        # Simplified: use longest stream segment
        length_km = streams_gdf.geometry.length.max() / 1000  # m to km
        
        # Centroid calculation
        centroid = gdf.geometry.centroid.iloc[0]
        
        # Centroidal length (distance from outlet to point on stream nearest centroid)
        # This requires spatial join - simplified here
        lc_km = length_km * 0.5  # Approximation (report shows Lc ≈ 0.53 * L for Ratu)
        
        # Elevation statistics from DEM
        with rasterio.open(self.dem_path) as src:
            dem_data = src.read(1)
            hmax_m = float(dem_data.max())
            hmin_m = float(dem_data.min())
        
        # Slope
        slope = (hmax_m - hmin_m) / length_km
        
        return {
            'A_km2': round(area_km2, 2),
            'L_km': round(length_km, 2),
            'Lc_km': round(lc_km, 2),
            'Hmax_m': round(hmax_m, 2),
            'Hmin_m': round(hmin_m, 2),
            'Slope': round(slope, 4)
        }