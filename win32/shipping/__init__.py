"""PDFMind Shipping & Polish layer.

UI polish, performance optimization, packaging, testing,
and Microsoft acquisition readiness.
"""

from .ui_polish import UIAnimations, Onboarding, Tooltips, InteractiveTutorial, TemplatesGallery, ThemeEngine
from .performance import LazyPageLoader, MemoryManager, CacheSystem, ParallelRenderer, StartupOptimizer
from .packaging import InstallerBuilder, PortableBuilder, AutoUpdater
from .testing import PDFCompatibilityTestSuite, PerformanceBenchmark, SecurityAuditSuite, AccessibilityTester
from .microsoft_ready import StoreListing, PricingTier, PitchDeck

__all__ = [
    "UIAnimations", "Onboarding", "Tooltips", "InteractiveTutorial",
    "TemplatesGallery", "ThemeEngine", "LazyPageLoader", "MemoryManager",
    "CacheSystem", "ParallelRenderer", "StartupOptimizer", "InstallerBuilder",
    "PortableBuilder", "AutoUpdater", "PDFCompatibilityTestSuite",
    "PerformanceBenchmark", "SecurityAuditSuite", "AccessibilityTester",
    "StoreListing", "PricingTier", "PitchDeck",
]
