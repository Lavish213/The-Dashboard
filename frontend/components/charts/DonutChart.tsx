'use client'

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'

interface DonutSlice {
  name: string
  value: number
  color: string
}

interface DonutChartProps {
  data: DonutSlice[]
  height?: number
}

export function DonutChart({ data, height = 200 }: DonutChartProps) {
  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius="55%"
          outerRadius="75%"
          paddingAngle={2}
          dataKey="value"
          strokeWidth={0}
        >
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: 'hsl(222 22% 9%)',
            border: '1px solid hsl(222 18% 14%)',
            borderRadius: '6px',
            fontSize: '12px',
            color: 'hsl(210 20% 96%)',
          }}
          formatter={(value: number) => [
            `${value} (${total > 0 ? Math.round((value / total) * 100) : 0}%)`,
          ]}
        />
        <Legend
          iconType="circle"
          iconSize={6}
          formatter={(value) => (
            <span style={{ fontSize: '11px', color: 'hsl(217 12% 55%)' }}>
              {value}
            </span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}