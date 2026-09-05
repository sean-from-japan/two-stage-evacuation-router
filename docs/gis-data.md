# Replacing synthetic fixtures with real map data

The committed scenario is synthetic. This note records what real Japanese data
would be needed instead, which parts are actually obtainable, and why none of it
is committed today. It is a feasibility record, not a plan that has been carried
out.

## What the model needs

The planner consumes four things: a routable road graph, positive edge weights,
hazard polygons, and shelter points. Three of them come from published sources.
The road graph is the one that does not.

## Licensing baseline

The National Land Numerical Information download site publishes under the Public
Data License 1.0 (PDL1.0), in force since 23 March 2026. Reuse and modification
are allowed with attribution, in the form
`出典：国土交通省国土数値情報ダウンロードサイト（URL）`, and edited data must not
be presented as if the state had produced it. Individual datasets carry their own
commercial/non-commercial condition that overrides the general permission, so the
licence has to be checked per dataset and, for hazard data, per prefecture.

## Dataset survey

| Need | Dataset | Formats | CRS | Vintage | Condition |
| --- | --- | --- | --- | --- | --- |
| Hazard polygons | Flood inundation areas (A31) | GML, Shapefile, GeoJSON | JGD2011 lat/lon | v4.0, 2022 | Varies by prefecture; several are open data with commercial use and redistribution allowed |
| Shelter points | Evacuation facilities (P20) | GML, Shapefile | JGD2000 lat/lon | 2012 | Non-commercial |
| Road graph | Roads (N01) | GML, Shapefile | JGD2000 and Tokyo Datum | 1995 | See site terms |

## Findings

**Hazard polygons are usable.** A31 ships as GeoJSON in a modern CRS and several
prefectures release it as open data permitting redistribution. This is the one
input that could be committed as a fixture with attribution.

**Shelter points are obtainable but weak.** P20 is limited to non-commercial use,
so committing it into an MIT-licensed repository would create a licence conflict.
It is also from 2012, and the publisher states it may not reflect current
designations. Real deployment would take shelter data from the responsible local
government instead.

**The road graph is the blocker.** N01 is based on a 1995 survey and its
specification explicitly declines to guarantee topological consistency, which is
exactly the property a shortest-path search depends on. It cannot be used as a
routing network. The realistic alternatives are OpenStreetMap, whose ODbL share-
alike terms would have to be reconciled with this repository's MIT licence, or the
national road base map database published by NILIM, whose terms need separate
review.

So the honest position is not that real data is unavailable. It is that hazard
geometry is available on good terms, shelters are available on terms that do not
fit this repository, and the routable network — the input the algorithm actually
consumes — is not available in a form that can be dropped in.

## Code changes a real adapter would require

- Give coordinates a declared CRS instead of treating them as a bare plane, and
  reproject the datasets, which do not currently share one.
- Derive edge weights from road geometry. Coordinates and weights are independent
  in the synthetic fixture; with real data they must agree.
- Add a GeoJSON scenario adapter beside the existing JSON one, leaving the planner
  untouched.
- Model segment-to-polygon intersection. Projecting a polygon onto endpoint nodes
  is adequate for a small synthetic graph and not for real road segments that
  cross a hazard boundary between two nodes.
- Carry provenance and an attribution string through to the rendered output.

## Sources

- Terms of use: <https://nlftp.mlit.go.jp/ksj/other/agreement.html>
- Flood inundation areas (A31): <https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A31-v2_1.html>
- Evacuation facilities (P20): <https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P20.html>
- Roads (N01): <https://nlftp.mlit.go.jp/ksj/gmlold/datalist/gmlold_KsjTmplt-N01.html>
- National road base map database: <https://www.jice.or.jp/road_basemap/>
