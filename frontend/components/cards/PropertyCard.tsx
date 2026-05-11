import * as React from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Home, MapPin, DollarSign, BedDouble, Bath, Square } from 'lucide-react'

export type PropertyStatus =
  | 'active'
  | 'pending'
  | 'sold'
  | 'off-market'
  | 'coming-soon'

export interface PropertyCardProps {
  id: string
  address: string
  city?: string
  status: PropertyStatus
  price?: string
  beds?: number
  baths?: number
  sqft?: number
  type?: string
  listedAt?: string
  agent?: string
  imageUrl?: string
  className?: string
  onClick?: () => void
}

const statusBadge: Record<PropertyStatus, string> = {
  active: 'active',
  pending: 'pending',
  sold: 'completed',
  'off-market': 'secondary',
  'coming-soon': 'info',
}

export function PropertyCard({
  address,
  city,
  status,
  price,
  beds,
  baths,
  sqft,
  type,
  listedAt,
  agent,
  imageUrl,
  className,
  onClick,
}: PropertyCardProps) {
  return (
    <Card
      className={cn(onClick && 'cursor-pointer hover:shadow-sm transition-shadow', className)}
      onClick={onClick}
    >
      {/* Thumbnail */}
      <div className="relative h-32 overflow-hidden rounded-t-lg bg-muted">
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={address}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-muted-foreground/40">
            <Home className="h-10 w-10" />
          </div>
        )}
        <div className="absolute right-2 top-2">
          <Badge
            variant={statusBadge[status] as Parameters<typeof Badge>[0]['variant']}
            className="text-[10px]"
          >
            {status}
          </Badge>
        </div>
      </div>

      <CardContent className="p-3 space-y-2">
        <div>
          <p className="text-sm font-medium truncate">{address}</p>
          {city && (
            <p className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <MapPin className="h-3 w-3" />
              {city}
            </p>
          )}
        </div>

        {price && (
          <p className="flex items-center gap-0.5 text-base font-semibold">
            <DollarSign className="h-4 w-4 text-muted-foreground" />
            {price}
          </p>
        )}

        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {beds !== undefined && (
            <span className="flex items-center gap-0.5">
              <BedDouble className="h-3.5 w-3.5" />
              {beds}
            </span>
          )}
          {baths !== undefined && (
            <span className="flex items-center gap-0.5">
              <Bath className="h-3.5 w-3.5" />
              {baths}
            </span>
          )}
          {sqft !== undefined && (
            <span className="flex items-center gap-0.5">
              <Square className="h-3.5 w-3.5" />
              {sqft.toLocaleString()} sqft
            </span>
          )}
          {type && <span className="ml-auto">{type}</span>}
        </div>

        {(agent || listedAt) && (
          <p className="text-[10px] text-muted-foreground">
            {agent && <span>{agent}</span>}
            {agent && listedAt && <span> · </span>}
            {listedAt && <span>{listedAt}</span>}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
