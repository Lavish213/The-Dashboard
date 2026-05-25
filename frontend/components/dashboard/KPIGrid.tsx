'use client'

import { SparklineChart } from '@/components/charts/SparklineChart'

interface KPITile {
  label: string
  value: string | number
  sub?: string
  trend?: number[]
  trendColor?: string
  highlight?: boolean
  gold?: boolean
}

function KPITile({ tile }: { tile: KPITile }) {
  const trendUp =
    tile.trend && tile.trend.length >= 2
      ? tile.trend[tile.trend.length - 1] > tile.trend[0]
      : null

  return (
    <div
      className={`rounded-lg border bg-card p-4 shadow-card flex flex-col gap-2 hover:shadow-card-hover transition-shadow ${
        tile.gold ? 'border-amber-500/20 bg-amber-500/5' : ''
      } ${tile.highlight ? 'border-teal-500/20 bg-teal-500/5' : ''}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground truncate">{tile.label}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-foreground leading-none">
            {tile.value}
          </p>
          {tile.sub && (
            <p className="text-xs text-muted-foreground mt-1">{tile.sub}</p>
          )}
        </div>
        {trendUp !== null && (
          <span
            className={`text-xs font-medium flex-shrink-0 ${
              trendUp ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {trendUp ? '↑' : '↓'}
          </span>
        )}
      </div>
      {tile.trend && tile.trend.length > 0 && (
        <div className="mt-auto">
          <SparklineChart
            data={tile.trend}
            color={tile.gold ? '#E6C27A' : tile.trendColor ?? '#5FCFCB'}
            height={28}
          />
        </div>
      )}
    </div>
  )
}

interface KPIGridProps {
  tiles: KPITile[]
  cols?: 2 | 3 | 4
}

export function KPIGrid({ tiles, cols = 4 }: KPIGridProps) {
  const colClass = {
    2: 'grid-cols-2',
    3: 'grid-cols-2 sm:grid-cols-3',
    4: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4',
  }[cols]

  return (
    <div className={`grid gap-3 ${colClass}`}>
      {tiles.map((tile) => (
        <KPITile key={tile.label} tile={tile} />
      ))}
    </div>
  )
}