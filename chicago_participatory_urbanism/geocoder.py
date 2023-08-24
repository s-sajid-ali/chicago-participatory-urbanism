import pandas as pd
import importlib.metadata
import logging
import geopandas as gpd
from shapely.ops import unary_union
from shapely.geometry import Point, MultiPoint, LineString, MultiLineString

# address point csv from https://hub-cookcountyil.opendata.arcgis.com/datasets/5ec856ded93e4f85b3f6e1bc027a2472_0/about
address_points_path = [p for p in importlib.metadata.files('chicago_participatory_urbanism')
                       if 'Address_Points_reduced.csv' in str(p)][0]
logging.info(f'Loading address points csv data from {address_points_path.locate()}')
df = pd.read_csv(address_points_path.locate())

# street center lines GeoJSON from https://data.cityofchicago.org/Transportation/Street-Center-Lines/6imu-meau
street_center_lines_path = [p for p in importlib.metadata.files('chicago_participatory_urbanism')
                       if 'Street Center Lines.geojson' in str(p)][0]
logging.info(f'Loading street center lines csv from {street_center_lines_path.locate()}')
gdf = gpd.read_file(street_center_lines_path.locate())

print("Data loaded.")



def get_street_address_coordinates_from_full_name(address: str):
    """
    Return the GPS coordinates of a street address in Chicago.

    Parameters:
    - address (string): A street address in Chicago matching the following format: "1763 W BELMONT AVE"

    Returns:
    - Point: A Shapely point with the GPS coordinates of the address (longitude, latitude).
    """
    result = df[df['CMPADDABRV'] == address.upper()]

    try:
        longitude = result["Long"].iloc[0]
        latitude = result["Lat"].iloc[0]
    except:
        (longitude, latitude) = (0,0)
    
    return Point(longitude, latitude)



def get_street_address_coordinates(address_number: int, direction_abbr: str, street_name: str, street_type_abbr: str, fuzziness: int = 10):
    """
    Return the GPS coordinates of a street address in Chicago.

    Parameters:
    - address_number (int): A street number in Chicago. Ex: 1736
    - direction_abbrev (str): An abbreviated cardinal direction. Ex: "W"
    - street_name (str): A street name in Chicago. Ex: "BELMONT"
    - street_type_abbr (str): An abbreviated street type. Ex: "AVE"
    - fuzziness (int): The number of addresses +/- the desired address number when searching for coordinates. The function will always return the closest address' coordinates.
        

    Returns:
    - Point: A Shapely point with the GPS coordinates of the address (longitude, latitude).
    """
    results = df[(address_number - fuzziness <= df['Add_Number']) &
                (df['Add_Number'] <= address_number + fuzziness) &
                (df['LSt_PreDir'] == direction_abbr.upper()) &
                (df['St_Name'] == street_name.upper()) &
                (df['LSt_Type'] == street_type_abbr.upper())].copy()
    
    # print(results[['Add_Number', 'St_Name','Long','Lat']])

    exact_address = results[results['Add_Number'] == address_number]

    try:
        if not exact_address.empty:
            # use exact address
            longitude = exact_address["Long"].iloc[0]
            latitude = exact_address["Lat"].iloc[0]
        else:
            # find closest address
            results['difference'] = abs(results['Add_Number'] - address_number)
            closest_index = results['difference'].idxmin()
            longitude = results.loc[closest_index, "Long"]
            latitude = results.loc[closest_index, "Lat"]
    except:
        print(f"Error finding coordinates for street address {address_number} {direction_abbr} {street_name} {street_type_abbr}")
        return None
    
    return Point(longitude, latitude)


def get_intersection_coordinates(street1: str, street2: str):
    """
    Return the GPS coordinates of an intersection in Chicago.

    Parameters:
    - street1 (str): A street name in Chicago. Ex: "BELMONT"
    - street2 (str): A street name in Chicago. Ex: "CLARK"

    Returns:
    - Point: A Shapely point with the GPS coordinates of the address (longitude, latitude).
    """
    if(street1 == street2):
        return None

    # select street shapes from data
    street1_data = gdf[gdf["street_nam"] == street1.upper()]
    street2_data = gdf[gdf["street_nam"] == street2.upper()]

    try:
        # join street shapes together
        street1_geometry = unary_union(street1_data['geometry'])
        street2_geometry = unary_union(street2_data['geometry'])

        intersection = street1_geometry.intersection(street2_geometry)

        if not intersection.is_empty:
            if isinstance(intersection, MultiPoint):
                # extract first point of multipoint
                ## (this tends to happen when one half of the intersecting street is offset from the other half)
                first_point = intersection.geoms[0]
                return 
            if isinstance(intersection, LineString):
                first_point = intersection.coords[0]
                return first_point
            if isinstance(intersection, MultiLineString):
                first_point = intersection.geoms[0].coords[0]
                return first_point
            else:
                return intersection
        else:
            return None
    except:
        print(f"Error getting intersection coordinates for {street1} & {street2}")
        return None
