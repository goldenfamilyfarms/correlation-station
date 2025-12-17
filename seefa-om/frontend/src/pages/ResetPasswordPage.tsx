import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Activity, Lock, CheckCircle2 } from 'lucide-react'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const token = searchParams.get('token')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setLoading(true)

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    setSuccess(true)
    setLoading(false)

    // Redirect to login after 2 seconds
    setTimeout(() => {
      navigate('/login')
    }, 2000)
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-muted/20 p-4">
        <Card className="w-full max-w-md shadow-2xl border-2">
          <CardHeader className="space-y-4 text-center">
            <div className="flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-500/10 text-green-600">
                <CheckCircle2 className="h-8 w-8" />
              </div>
            </div>
            <div>
              <CardTitle className="text-2xl font-bold">Password Reset Successful</CardTitle>
              <CardDescription className="text-base mt-2">
                Your password has been reset successfully
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <Button
              asChild
              className="w-full"
            >
              <Link to="/login">Go to Login</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-muted/20 p-4">
      <Card className="w-full max-w-md shadow-2xl border-2">
        <CardHeader className="space-y-4 text-center">
          <div className="flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-lg">
              <Activity className="h-8 w-8" />
            </div>
          </div>
          <div>
            <CardTitle className="text-3xl font-bold">Reset Password</CardTitle>
            <CardDescription className="text-base mt-2">
              Enter your new password below
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
                {error}
              </div>
            )}
            {!token && (
              <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
                Invalid or missing reset token. Please request a new password reset.
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="password" className="flex items-center gap-2">
                <Lock className="h-4 w-4" />
                New Password
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter new password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="h-11"
                disabled={!token}
              />
              <p className="text-xs text-muted-foreground">
                Must be at least 8 characters
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword" className="flex items-center gap-2">
                <Lock className="h-4 w-4" />
                Confirm Password
              </Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="h-11"
                disabled={!token}
              />
            </div>
            <Button
              type="submit"
              className="w-full h-11 text-base font-semibold"
              disabled={loading || !token}
            >
              {loading ? 'Resetting...' : 'Reset Password'}
            </Button>
            <Button
              type="button"
              variant="ghost"
              asChild
              className="w-full"
            >
              <Link to="/login">Back to Login</Link>
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

