# P0 data dictionary

The definitions below are paraphrased from the official BTS TranStats field page.

| Field | P0 use |
|---|---|
| `FlightDate` | Scheduled flight date; base local date for departure. |
| `Reporting_Airline` / `DOT_ID_Reporting_Airline` | Reporting carrier identifiers. |
| `Tail_Number` | Aircraft identifier used to reconstruct rotations. It may be blank when a canceled flight never received an aircraft assignment. |
| `Flight_Number_Reporting_Airline` | Reporting carrier flight number. |
| `OriginAirportID`, `Origin` | Stable origin ID and IATA code. |
| `DestAirportID`, `Dest` | Stable destination ID and IATA code. |
| `CRSDepTime`, `CRSArrTime` | Scheduled local departure and arrival clocks in HHMM format. |
| `DepTime`, `ArrTime` | Actual local departure and arrival clocks in HHMM format. |
| `DepDelay`, `ArrDelay` | Signed schedule deviations in minutes; early operations are negative. |
| `Cancelled`, `CancellationCode` | Cancellation flag and reason category. |
| `Diverted` | Diversion flag; diverted flights are not silently treated as normal chain legs. |
| `CRSElapsedTime`, `ActualElapsedTime` | Gate-to-gate scheduled and actual duration in minutes. |
| `TaxiOut`, `TaxiIn`, `AirTime`, `Distance` | Operational context and basic validity checks. |
| `CarrierDelay`, `WeatherDelay`, `NASDelay`, `SecurityDelay`, `LateAircraftDelay` | Reported delay-cause minutes. `LateAircraftDelay` is compared with the reconstructed upstream-delay signal. |

Official field reference: <https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ>

