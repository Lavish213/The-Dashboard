import * as React from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Phone, Mail, MapPin } from 'lucide-react'

export type LeadStatus =
  | 'new'
  | 'contacted'
  | 'qualified'
  | 'nurturing'
  | 'hot'
  | 'converted'
  | 'lost'

export interface LeadCardProps {
  id: string
  name: string
  email?: string
  phone?: string
  location?: string
  status: LeadStatus
  score?: number
  source?: string
  assignedTo?: string
  lastActivity?: string
  budget?: string
  className?: string
  onClick?: () => void
}

const statusBadge: Record<LeadStatus, string> = {
  new: 'info',
  contacted: 'pending',
  qualified: 'active',
  nurturing: 'secondary',
  hot: 'escalated',
  converted: 'completed',
  lost: 'failed',
}

function initials(name: string) {
  return name
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export function LeadCard({
  name,
  email,
  phone,
  location,
  status,
  score,
  source,
  assignedTo,
  lastActivity,
  budget,
  className,
  onClick,
}: LeadCardProps) {
  return (
    <Card
      className={cn(onClick && 'cursor-pointer hover:shadow-sm transition-shadow', className)}
      onClick={onClick}
    >
      <CardContent className="p-3 space-y-2.5">
        <div className="flex items-center gap-2.5">
          <Avatar size="md">
            <AvatarFallback>{initials(name)}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-1">
              <p className="text-sm font-medium truncate">{name}</p>
              <Badge
                variant={statusBadge[status] as Parameters<typeof Badge>[0]['variant']}
                className="flex-shrink-0 text-[10px]"
              >
                {status}
              </Badge>
            </div>
            {source && (
              <p className="text-[10px] text-muted-foreground">Source: {source}</p>
            )}
          </div>
        </div>

        <div className="space-y-0.5">
          {email && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Mail className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">{email}</span>
            </div>
          )}
          {phone && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Phone className="h-3 w-3 flex-shrink-0" />
              <span>{phone}</span>
            </div>
          )}
          {location && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <MapPin className="h-3 w-3 flex-shrink-0" />
              <span className="truncate">{location}</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
          <div className="flex items-center gap-2">
            {score !== undefined && (
              <span>Score: <span className="font-medium text-foreground">{score}</span></span>
            )}
            {budget && (
              <span>Budget: <span className="font-medium text-foreground">{budget}</span></span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {assignedTo && <span>→ {assignedTo}</span>}
            {lastActivity && <span>{lastActivity}</span>}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
