/**
 * Coordinate transformations between GeoJSON [lon, lat] and Mobile Map {lat, lon}.
 */

export interface LatLng {
  latitude: number;
  longitude: number;
}

/**
 * Converts a GeoJSON [longitude, latitude] pair to a React Native Map LatLng object.
 */
export function geoJsonToLatLng(coords: [number, number]): LatLng {
  return {
    longitude: coords[0],
    latitude: coords[1],
  };
}

/**
 * Converts an array of GeoJSON coordinates to LatLng objects.
 */
export function geoJsonLineStringToLatLngs(coords: Array<[number, number]>): LatLng[] {
  return coords.map(geoJsonToLatLng);
}
