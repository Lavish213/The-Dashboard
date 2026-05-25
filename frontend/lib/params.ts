import { parseAsInteger, parseAsString } from 'nuqs'

export const leadsParams = {
  status: parseAsString.withDefault(''),
}

export const callsParams = {
  call_status: parseAsString.withDefault(''),
  page: parseAsInteger.withDefault(1),
}

export const workflowsParams = {
  workflow_status: parseAsString.withDefault(''),
}

export const auditParams = {
  page: parseAsInteger.withDefault(1),
  action: parseAsString.withDefault(''),
  target_type: parseAsString.withDefault(''),
}

export const activityParams = {
  page: parseAsInteger.withDefault(1),
  event_type: parseAsString.withDefault(''),
}