"""Wall-clock telemetry is never physical process time."""
import math
import resource
import time


class Budget:
    def __init__(self,active,ceiling,phase):
        self.start=time.monotonic(); self.active=active; self.ceiling=ceiling; self.phase=phase
        self.completed=[]; self.pending=[]

    def check(self):
        if self.active is not None and time.monotonic()-self.start>self.active: raise TimeoutError('wall_budget')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024>512: raise RuntimeError('rss_resource_limit')

    def snapshot(self,status,reason=None):
        return dict(active_budget_seconds=self.active,ceiling_budget_seconds=self.ceiling,
                    elapsed_wall_seconds=time.monotonic()-self.start,
                    peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                    workers=1,threads=1,phase=self.phase,completed_scenario_ids=list(self.completed),
                    pending_scenario_ids=list(self.pending),status=status,reason=reason)


def parse_budget(value,ceiling):
    try: v=float(value)
    except (ValueError,TypeError): raise ValueError('budget_parse_rejected') from None
    if not math.isfinite(v) or not 0<v<=ceiling: raise ValueError('budget_parse_rejected')
    return v
