import datetime
from typing import Optional, Dict, Any

import requests


class OpenMeteoClient:
	"""Lightweight client for Open-Meteo current weather and forecast.

	- No API key required.
	- Supports city name via geocoding or direct lat/lon.
	Docs: https://open-meteo.com/
	"""

	GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
	METEO_URL = "https://api.open-meteo.com/v1/forecast"

	def geocode(self, query: str, country_code: Optional[str] = "IN") -> Optional[Dict[str, Any]]:
		"""Return first geocoding match for a place query.

		Example return: { name, latitude, longitude, country_code, admin1 }
		"""
		if not query:
			return None
		params = {
			"name": query,
			"count": 1,
			"language": "en",
		}
		if country_code:
			params["country_code"] = country_code
		r = requests.get(self.GEO_URL, params=params, timeout=10)
		r.raise_for_status()
		data = r.json() or {}
		results = data.get("results") or []
		if not results:
			return None
		top = results[0]
		return {
			"name": top.get("name"),
			"latitude": top.get("latitude"),
			"longitude": top.get("longitude"),
			"country_code": top.get("country_code"),
			"admin1": top.get("admin1"),
		}

	def forecast(self, lat: float, lon: float, tz: str = "auto") -> Dict[str, Any]:
		"""Fetch current and 7-day forecast summary."""
		params = {
			"latitude": lat,
			"longitude": lon,
			"current": [
				"temperature_2m",
				"apparent_temperature",
				"is_day",
				"precipitation",
				"wind_speed_10m",
				"wind_direction_10m",
				"relative_humidity_2m",
				"weather_code",
			],
			"daily": [
				"temperature_2m_max",
				"temperature_2m_min",
				"precipitation_sum",
				"precipitation_probability_max",
				"precipitation_hours",
				"sunrise",
				"sunset",
				"weather_code",
			],
			"timezone": tz,
		}
		r = requests.get(self.METEO_URL, params=params, timeout=15)
		r.raise_for_status()
		data = r.json() or {}
		return self._normalize(data)

	@staticmethod
	def _normalize(payload: Dict[str, Any]) -> Dict[str, Any]:
		current = payload.get("current", {})
		daily = payload.get("daily", {})

		# Build day-wise list
		days = []
		times = (daily.get("time") or [])
		for i, day in enumerate(times):
			days.append({
				"date": day,
				"t_max": (daily.get("temperature_2m_max") or [None])[i],
				"t_min": (daily.get("temperature_2m_min") or [None])[i],
				"precip": (daily.get("precipitation_sum") or [None])[i],
				"prob": (daily.get("precipitation_probability_max") or [None])[i],
				"precip_hours": (daily.get("precipitation_hours") or [None])[i],
				"sunrise": (daily.get("sunrise") or [None])[i],
				"sunset": (daily.get("sunset") or [None])[i],
				"code": (daily.get("weather_code") or [None])[i],
			})

		# Rain summary
		today_prob = None
		if days:
			try:
				today_prob = days[0].get("prob")
			except Exception:
				pass
		next_rain = None
		for d in days:
			prob = d.get("prob") or 0
			precip = d.get("precip") or 0
			# Consider it a rain day if probability >= 30% or measurable precip expected
			if (isinstance(prob, (int, float)) and prob >= 30) or (isinstance(precip, (int, float)) and precip > 0):
				next_rain = d
				break

		return {
			"timezone": payload.get("timezone"),
			"current": {
				"temp": current.get("temperature_2m"),
				"feels_like": current.get("apparent_temperature"),
				"humidity": current.get("relative_humidity_2m"),
				"wind_speed": current.get("wind_speed_10m"),
				"wind_dir": current.get("wind_direction_10m"),
				"precip": current.get("precipitation"),
				"is_day": current.get("is_day"),
				"code": current.get("weather_code"),
			},
			"daily": days,
			"rain": {
				"today_prob": today_prob,
				"next_rain": next_rain,
			},
		}


def get_weather_for_query(query: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
	"""Convenience function to get weather using a city query or lat/lon.

	Prefers explicit lat/lon if provided; otherwise uses geocoding for query.
	"""
	client = OpenMeteoClient()
	if lat is not None and lon is not None:
		return client.forecast(lat, lon)
	if query:
		geo = client.geocode(query)
		if not geo:
			raise ValueError("Location not found")
		return client.forecast(geo["latitude"], geo["longitude"]) | {"place": geo}
	raise ValueError("Provide a city name or coordinates")

