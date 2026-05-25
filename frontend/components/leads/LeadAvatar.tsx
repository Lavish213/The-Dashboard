'use client'

import { AvatarScore } from '@/components/ui/avatar-score'

interface LeadAvatarProps {
  name: string
  score?: number | null
  size?: 'sm' | 'md' | 'lg'
}

export function LeadAvatar({ name, score, size = 'md' }: LeadAvatarProps) {
  return <AvatarScore name={name} score={score} size={size} />
}