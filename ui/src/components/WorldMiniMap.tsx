import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
} from "react-simple-maps";

const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@3/countries-110m.json";

interface WorldMiniMapProps {
  lat: number;
  lon: number;
  label?: string;
}

export default function WorldMiniMap({ lat, lon, label }: WorldMiniMapProps) {
  return (
    <div className="relative w-full">
      <ComposableMap
        projection="geoEqualEarth"
        projectionConfig={{ scale: 150 }}
        width={800}
        height={380}
        style={{ width: "100%", height: "auto" }}
      >
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo) => (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                style={{
                  default: {
                    fill: "hsl(var(--muted) / 0.35)",
                    stroke: "hsl(var(--border))",
                    strokeWidth: 0.4,
                    outline: "none",
                  },
                  hover: {
                    fill: "hsl(var(--muted) / 0.35)",
                    stroke: "hsl(var(--border))",
                    strokeWidth: 0.4,
                    outline: "none",
                  },
                  pressed: {
                    fill: "hsl(var(--muted) / 0.35)",
                    stroke: "hsl(var(--border))",
                    strokeWidth: 0.4,
                    outline: "none",
                  },
                }}
              />
            ))
          }
        </Geographies>
        <Marker coordinates={[lon, lat]}>
          <circle
            r={8}
            fill="hsl(var(--primary) / 0.18)"
            stroke="none"
          />
          <circle
            r={3.5}
            fill="hsl(var(--primary))"
            stroke="hsl(var(--background))"
            strokeWidth={1.2}
          />
        </Marker>
      </ComposableMap>
      {label && (
        <div className="mt-2 text-center font-mono text-[10.5px] text-muted-foreground">
          {label}
        </div>
      )}
    </div>
  );
}
