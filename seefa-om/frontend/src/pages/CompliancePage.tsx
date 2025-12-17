import { Shield, Users, BookOpen, Code, Network, FileText, ExternalLink, Link as LinkIcon } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'

export default function CompliancePage() {
  return (
    <div className="space-y-8 animate-in fade-in-50 duration-700">
      {/* Page Header */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-1 w-16 bg-gradient-to-r from-orange-500 to-red-500 rounded-full" />
          <Badge variant="outline" className="text-xs font-semibold">Updated Dec 08, 2025</Badge>
        </div>
        <div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4 bg-gradient-to-r from-foreground via-foreground/90 to-foreground/70 bg-clip-text">
            Compliance & SECA Team
          </h1>
          <p className="text-lg md:text-xl text-muted-foreground max-w-3xl leading-relaxed">
            Created by Kbrennan, Michael K, last updated by Moser, Nancy on Dec 08, 2025 • 8 minute read
          </p>
        </div>
      </div>

      <Separator className="my-8" />

      {/* Mission Section */}
      <Card className="hover:shadow-xl transition-all duration-500 border border-border/50 bg-gradient-to-br from-card to-card/95 backdrop-blur-sm">
        <CardHeader className="border-b border-border/30 bg-gradient-to-r from-orange-500/10 to-red-500/10">
          <CardTitle className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6 text-orange-600" />
            Mission
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <p className="text-base leading-relaxed mb-4">
            To work collaboratively, increase workflow efficiency, and provide our company and Spectrum Business boundary partners with automation support for the Compliance workstream.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div>
              <p className="text-sm font-semibold text-muted-foreground mb-1">Team DL</p>
              <p className="text-sm">DL-SBNOE-SBE-AERO-Compliance</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-muted-foreground mb-1">Product Owner</p>
              <p className="text-sm">Donny Newsome</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-muted-foreground mb-1">Jira Project</p>
              <p className="text-sm">SECA Intake</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Supported Business Value Automations */}
      <div>
        <h2 className="text-3xl font-bold mb-4">Supported Business Value Automations</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">Network Compliance</CardTitle>
              <CardDescription>New/MAC/Disconnect</CardDescription>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">Network Acceptance</CardTitle>
              <CardDescription>Device TACACS accessibility</CardDescription>
            </CardHeader>
          </Card>
        </div>
      </div>

      {/* MDSO Compliance Products */}
      <div>
        <h2 className="text-3xl font-bold mb-4">MDSO Compliance Products</h2>
        <p className="text-muted-foreground mb-4">Service Mapper Suite</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">Service Mapper</CardTitle>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">Disconnect Mapper</CardTitle>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">WIA Mapper</CardTitle>
            </CardHeader>
          </Card>
        </div>
      </div>

      {/* SEnSE Compliance Microservices */}
      <div>
        <h2 className="text-3xl font-bold mb-4">SEnSE Compliance Microservices</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Code className="h-5 w-5" />
                Palantir
              </CardTitle>
              <CardDescription>palantir/v1/compliance/*</CardDescription>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Code className="h-5 w-5" />
                Beorn
              </CardTitle>
              <CardDescription>beorn/v1/eligibility/compliance_*</CardDescription>
            </CardHeader>
          </Card>
        </div>
      </div>

      {/* Core Skills and Frameworks */}
      <div>
        <h2 className="text-3xl font-bold mb-4">Core Skills and Frameworks</h2>
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className="text-sm px-3 py-1">Python</Badge>
          <Badge variant="outline" className="text-sm px-3 py-1">Network Engineering</Badge>
          <Badge variant="outline" className="text-sm px-3 py-1">Blue Planet Orchestrator (MDSO)</Badge>
          <Badge variant="outline" className="text-sm px-3 py-1">REST APIs (Flask, Fast API)</Badge>
        </div>
      </div>

      {/* Quick Links */}
      <div>
        <h2 className="text-3xl font-bold mb-4">Quick Links</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50 cursor-pointer group">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 group-hover:text-primary transition-colors">
                <LinkIcon className="h-5 w-5" />
                SECA Scrum Board
              </CardTitle>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50 cursor-pointer group">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 group-hover:text-primary transition-colors">
                <LinkIcon className="h-5 w-5" />
                SECA Focus + BV
              </CardTitle>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50 cursor-pointer group">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 group-hover:text-primary transition-colors">
                <LinkIcon className="h-5 w-5" />
                AERO Releases
              </CardTitle>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50 cursor-pointer group">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 group-hover:text-primary transition-colors">
                <LinkIcon className="h-5 w-5" />
                Team Demos
              </CardTitle>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50 cursor-pointer group">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 group-hover:text-primary transition-colors">
                <LinkIcon className="h-5 w-5" />
                Business EXPO Overview
              </CardTitle>
            </CardHeader>
          </Card>
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50 cursor-pointer group">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 group-hover:text-primary transition-colors">
                <LinkIcon className="h-5 w-5" />
                Developer Proposed Workflow
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      </div>

      {/* Team Support */}
      <div>
        <h2 className="text-3xl font-bold mb-4">Team Support</h2>
        <Card className="hover:shadow-xl transition-all duration-500 border border-border/50">
          <CardHeader>
            <CardTitle className="text-lg">Team Chat Assignments: thru EOY - 2025</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h3 className="font-semibold mb-2">SBEFA - Compliance</h3>
              <p className="text-sm text-muted-foreground">• Robert/Mickey (Both Primary)</p>
              <p className="text-sm text-muted-foreground">• (Both Backup for Acceptance)</p>
            </div>
            <Separator />
            <div>
              <h3 className="font-semibold mb-2">SBEFA - Acceptance</h3>
              <p className="text-sm text-muted-foreground">• Alex/Taha (Both Primary)</p>
              <p className="text-sm text-muted-foreground">• (Both Backup for Compliance)</p>
            </div>
            <Separator />
            <div>
              <h3 className="font-semibold mb-2">SBEFA - Disconnect + MS Acceptance & Compliance</h3>
              <p className="text-sm text-muted-foreground">• Matt/Derrick (Both Primary)</p>
              <p className="text-sm text-muted-foreground">• Matt (Backup Compliance)</p>
              <p className="text-sm text-muted-foreground">• Derrick (Backup Acceptance)</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Additional Resources */}
      <div>
        <h2 className="text-3xl font-bold mb-4">Additional Resources</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">Compliance Automation</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• Compliance Automation Error Codes</li>
                <li>• Compliance Automation Process</li>
                <li>• Compliance Flow Charts</li>
                <li>• Device Validator</li>
                <li>• Network Compliance Automation Eligibility</li>
              </ul>
            </CardContent>
          </Card>
          <Card className="hover:shadow-xl transition-all duration-500 border border-border/50">
            <CardHeader>
              <CardTitle className="text-lg">AERO Project Planning</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>• SEEFA Priorities by Business Value</li>
                <li>• SECA Team Focus</li>
                <li>• CPEA Sprint Focus</li>
                <li>• SENOESD Sprint Focus</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

