'use client'

import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts'

interface SparklineChartProps {
  data: number[]
  color?: string
  height?: number
}

export function SparklineChart({
  data,
  color = '#5FCFCB',
  height = 32,
}: SparklineChartProps) {
  const chartData = data.map((value, index) => ({ index, value }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData}>
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
        <Tooltip
          content={() => null}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}