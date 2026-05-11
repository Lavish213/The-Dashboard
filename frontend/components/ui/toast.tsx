/**
 * Toast — re-exports sonner's Toaster which is already mounted in ToastProvider
 * Use the `toast` function directly from 'sonner' in application code
 *
 * @example
 * import { toast } from 'sonner'
 * toast.success('Workflow complete')
 * toast.error('Action failed')
 * toast.warning('Approval required')
 * toast.info('Syncing…')
 * toast.loading('Processing…')
 */
export { toast, Toaster } from 'sonner'
export type { ToasterProps } from 'sonner'
