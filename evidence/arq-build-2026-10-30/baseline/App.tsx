import { useState, useEffect } from 'react';
import { PlanRun, SolverJob, SystemHealth, OperationalEvent, IntelligenceEvidence } from './types/api';
import { apiClient } from './api/client';
import { Navbar } from './components/layout/Navbar';
import { SidebarRail, NavView } from './components/layout/SidebarRail';
import { CommandCenterView } from './features/dashboard/CommandCenterView';
import { FleetOperationsView } from './features/fleet/FleetOperationsView';
import { DispatchPlanningView } from './features/dispatch/DispatchPlanningView';
import { SlaRiskView } from './features/risk/SlaRiskView';
import { IntelligenceView } from './features/intelligence/IntelligenceView';
import { ActivityView } from './features/activity/ActivityView';
import { JobsView } from './features/jobs/JobsView';
import { DriverTerminalView } from './features/terminal/DriverTerminalView';
import { CheckCircle2, AlertTriangle, X } from 'lucide-react';

import {
  BENGALURU_SCENARIO,
  SOLOMON_SCENARIO,
  INTELLIGENCE_EVIDENCE,
  OPERATIONAL_EVENTS,
  DEFAULT_HEALTH
} from './data/mockScenarios';

export default function App() {
  const [plans, setPlans] = useState<PlanRun[]>([BENGALURU_SCENARIO, SOLOMON_SCENARIO]);
  const [activePlanId, setActivePlanId] = useState<string>('run-blr-20261029-01');
  const [currentView, setCurrentView] = useState<NavView>('command');
  const [health, setHealth] = useState<SystemHealth>(DEFAULT_HEALTH);
  const [jobs, setJobs] = useState<SolverJob[]>([]);
  const [events, setEvents] = useState<OperationalEvent[]>(OPERATIONAL_EVENTS);
  const [evidence, setEvidence] = useState<IntelligenceEvidence>(INTELLIGENCE_EVIDENCE);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(BENGALURU_SCENARIO.vehicles[0].id);
  const [selectedStopId, setSelectedStopId] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'warning' } | null>(null);

  // Initial load
  useEffect(() => {
    let mounted = true;
    async function loadData() {
      try {
        const initialPlans = await apiClient.getRuns();
        if (mounted && initialPlans.length > 0) {
          setPlans(initialPlans);
          setActivePlanId((prev) => prev || initialPlans[0].id);
          setSelectedVehicleId((prev) => prev || initialPlans[0].vehicles[0]?.id || null);
        }
      } catch (e) {
        console.warn('[arQ] Using cached scenarios:', e);
      }

      try {
        const initialHealth = await apiClient.getHealth();
        if (mounted) setHealth(initialHealth);
      } catch {
        // Handled internally by apiClient
      }

      try {
        const initialJobs = await apiClient.getJobs();
        if (mounted) setJobs(initialJobs);
      } catch {
        // Backend not ready yet
      }

      try {
        const initialEvents = await apiClient.getOperationalEvents();
        if (mounted) setEvents(initialEvents);
      } catch {
        // Fallback to initial events
      }

      try {
        const initialEvidence = await apiClient.getIntelligenceEvidence();
        if (mounted) setEvidence(initialEvidence);
      } catch {
        // Fallback to bundled evidence
      }
    }
    loadData();
    return () => { mounted = false; };
  }, []);

  // Periodic polling for jobs, health, and events
  useEffect(() => {
    let mounted = true;
    const interval = setInterval(async () => {
      try {
        const updatedJobs = await apiClient.getJobs();
        if (mounted) setJobs(updatedJobs);
      } catch {
        // Polling retry on next tick
      }

      try {
        const updatedHealth = await apiClient.getHealth();
        if (mounted) setHealth(updatedHealth);
      } catch {
        // Polling retry
      }

      try {
        const updatedEvents = await apiClient.getOperationalEvents();
        if (mounted) setEvents(updatedEvents);
      } catch {
        // Polling retry
      }

      try {
        const updatedRuns = await apiClient.getRuns();
        if (mounted && updatedRuns && updatedRuns.length > 0) {
          setPlans(updatedRuns);
        }
      } catch {
        // Polling retry
      }
    }, 3000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const activePlan = plans.find((p) => p.id === activePlanId) || plans[0];

  const handlePlanSelect = (id: string) => {
    setActivePlanId(id);
    const chosenPlan = plans.find((p) => p.id === id);
    if (chosenPlan && chosenPlan.vehicles.length > 0) {
      setSelectedVehicleId(chosenPlan.vehicles[0].id);
    } else {
      setSelectedVehicleId(null);
    }
    setSelectedStopId(null);
  };

  const handlePlanUpdate = (updated: PlanRun) => {
    setPlans((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    setNotification({
      message: `Manifest updated: ${updated.scenario_name}`,
      type: 'success'
    });
  };

  const handleTriggerReplan = async (stopId: string, vehicleId: string) => {
    if (!activePlan) return;
    try {
      const res = await apiClient.executeRecoveryReplan({
        run_id: activePlan.id,
        vehicle_id: vehicleId,
        delayed_stop_id: stopId,
        delay_minutes: 20,
        locked_stop_ids: activePlan.routes
          .find((r) => r.vehicle_id === vehicleId)
          ?.stops.filter((s) => s.is_completed || s.is_locked)
          .map((s) => s.id) || []
      });

      if (res.success) {
        const updatedRuns = await apiClient.getRuns();
        setPlans(updatedRuns);
        setNotification({
          message: `Recovery committed: ${res.audit_log}`,
          type: 'success'
        });
        const updatedEvents = await apiClient.getOperationalEvents();
        setEvents(updatedEvents);
      }
    } catch (err: any) {
      setNotification({
        message: err?.message || 'Recovery replanning refused: display fixtures cannot be mutated.',
        type: 'warning'
      });
    }
  };

  const runningJobsCount = jobs.filter((j) => j.status === 'running' || j.status === 'queued').length;

  return (
    <div className="flex flex-col h-screen w-screen bg-[#F5F3ED] text-[#141F1A] font-sans antialiased overflow-hidden">
      {/* Global Toast Notification */}
      {notification && (
        <div className="fixed top-18 right-6 z-50 glass-panel-strong px-4 py-3 rounded-2xl shadow-xl border border-black/5 flex items-center space-x-3 text-xs animate-in slide-in-from-top-2 duration-200">
          {notification.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-[#1E5A44] shrink-0" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-[#D97706] shrink-0" />
          )}
          <span className="font-semibold text-[#141F1A] max-w-sm">
            {notification.message}
          </span>
          <button
            onClick={() => setNotification(null)}
            className="p-1 rounded-lg hover:bg-black/5 text-[#7D8D85]"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Top Navigation Bar */}
      {activePlan && (
        <Navbar
          currentPlan={activePlan}
          allPlans={plans}
          onSelectPlan={handlePlanSelect}
          health={health}
          onRefreshHealth={async () => {
            const h = await apiClient.getHealth();
            setHealth(h);
          }}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          activeJobsCount={runningJobsCount}
        />
      )}

      {/* Body: Sidebar Rail + View Area */}
      <div className="flex-1 flex overflow-hidden">
        <SidebarRail
          currentView={currentView}
          onSelectView={setCurrentView}
          activeJobsCount={runningJobsCount}
          health={health}
        />

        {/* View Switcher Container */}
        <main className="flex-1 flex flex-col overflow-hidden relative">
          {activePlan ? (
            <>
              {currentView === 'command' && (
                <CommandCenterView
                  plan={activePlan}
                  selectedVehicleId={selectedVehicleId}
                  selectedStopId={selectedStopId}
                  onSelectVehicle={setSelectedVehicleId}
                  onSelectStop={setSelectedStopId}
                  searchQuery={searchQuery}
                  onPlanUpdate={handlePlanUpdate}
                  onTriggerReplan={handleTriggerReplan}
                />
              )}

              {currentView === 'fleet' && (
                <FleetOperationsView
                  plan={activePlan}
                  selectedVehicleId={selectedVehicleId}
                  searchQuery={searchQuery}
                  onSelectVehicleForMap={(vId) => {
                    setSelectedVehicleId(vId);
                    setSelectedStopId(null);
                    setCurrentView('command');
                  }}
                />
              )}

              {currentView === 'dispatch' && (
                <DispatchPlanningView
                  plan={activePlan}
                  onPlanUpdate={handlePlanUpdate}
                  onSelectRoute={(vehicleId) => {
                    setSelectedVehicleId(vehicleId);
                    setSelectedStopId(null);
                    setCurrentView('command');
                  }}
                  onJobTriggered={async () => {
                    const updatedJobs = await apiClient.getJobs();
                    setJobs(updatedJobs);
                  }}
                />
              )}

              {currentView === 'risk' && (
                <SlaRiskView
                  plan={activePlan}
                  onInspectStop={(stopId, vehicleId) => {
                    setSelectedVehicleId(vehicleId);
                    setSelectedStopId(stopId);
                    setCurrentView('command');
                  }}
                />
              )}

              {currentView === 'intelligence' && evidence && (
                <IntelligenceView evidence={evidence} />
              )}

              {currentView === 'activity' && (
                <ActivityView
                  events={events}
                  onRefresh={async () => {
                    const evts = await apiClient.getOperationalEvents();
                    setEvents(evts);
                  }}
                />
              )}

              {currentView === 'jobs' && (
                <JobsView
                  jobs={jobs}
                  health={health}
                  onRefreshJobs={async () => {
                    const j = await apiClient.getJobs();
                    setJobs(j);
                  }}
                />
              )}

              {currentView === 'terminal' && (
                <DriverTerminalView />
              )}
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-xs text-[#68756F]">
              Loading arQ logistics scenario…
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
