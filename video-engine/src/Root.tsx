// ─────────────────────────────────────────────────────────────
// PrimeEdge Video Engine · Root Composition Registry
// ─────────────────────────────────────────────────────────────
import React from "react";
import { Composition } from "remotion";
import { SignalCard, defaultSignalCardProps } from "./compositions/SignalCard";
import { WeeklyWrapped, defaultWeeklyWrappedProps } from "./compositions/WeeklyWrapped";
import { MacroDaily, defaultMacroDailyProps } from "./compositions/MacroDaily";
import { MarketingHero, defaultMarketingHeroProps } from "./compositions/MarketingHero";
import { MarketingV2, defaultMarketingV2Props } from "./compositions/MarketingV2";
import { MarketingHybrid, defaultMarketingHybridProps } from "./compositions/MarketingHybrid";
import { MarketingHybridVertical, defaultMarketingHybridVerticalProps } from "./compositions/MarketingHybrid/vertical";
import { RegimePerformance, defaultRegimePerformanceProps } from "./compositions/RegimePerformance";
import { HiddenState, defaultHiddenStateProps } from "./compositions/HiddenState";
import { TemplateA, defaultTemplateAProps } from "./compositions/TemplateA";
import { LimitVsMarket, defaultLimitVsMarketProps } from "./compositions/LimitVsMarket";
import type { SignalCardData } from "./compositions/SignalCard";
import type { WeeklyWrappedData } from "./compositions/WeeklyWrapped";
import type { MacroDailyData } from "./compositions/MacroDaily";
import type { MarketingHeroData } from "./compositions/MarketingHero";
import type { MarketingV2Data } from "./compositions/MarketingV2";
import type { MarketingHybridData } from "./compositions/MarketingHybrid";
import type { MarketingHybridVerticalData } from "./compositions/MarketingHybrid/vertical";
import type { RegimePerformanceData } from "./compositions/RegimePerformance";
import type { HiddenStateData } from "./compositions/HiddenState";
import type { TemplateAData } from "./compositions/TemplateA";
import { MARKETING_TOTAL_FRAMES } from "./compositions/MarketingHero/timing";
import { V2_TOTAL_FRAMES } from "./compositions/MarketingV2/timing";
import { HYBRID_TOTAL_FRAMES } from "./compositions/MarketingHybrid/timing";
import { REGIME_TOTAL_FRAMES } from "./compositions/RegimePerformance/timing";
import { HIDDEN_TOTAL_FRAMES } from "./compositions/HiddenState/timing";
import { TEMPLATE_A_TOTAL_FRAMES } from "./compositions/TemplateA/timing";
import { LIMIT_VS_MARKET_TOTAL_FRAMES } from "./compositions/LimitVsMarket/timing";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* ── Signal Card ─────────────────────────────────────────
          5 seconds · 30fps · 150 frames · 1080×1920 (9:16)
      */}
      <Composition<SignalCardData>
        id="SignalCard"
        component={SignalCard}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultSignalCardProps}
      />

      {/* ── Weekly Wrapped ───────────────────────────────────────
          15 seconds · 30fps · 450 frames · 1080×1920 (9:16)
      */}
      <Composition<WeeklyWrappedData>
        id="WeeklyWrapped"
        component={WeeklyWrapped}
        durationInFrames={450}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultWeeklyWrappedProps}
      />

      {/* ── Macro Daily ──────────────────────────────────────────
          8 seconds · 30fps · 240 frames · 1080×1920 (9:16)
      */}
      <Composition<MacroDailyData>
        id="MacroDaily"
        component={MacroDaily}
        durationInFrames={240}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultMacroDailyProps}
      />

      {/* ── Marketing Hero ───────────────────────────────────────
          ~68 s · 30fps · 1920×1080 (16:9) · VO + music bed
      */}
      <Composition<MarketingHeroData>
        id="MarketingHero"
        component={MarketingHero}
        durationInFrames={MARKETING_TOTAL_FRAMES}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={defaultMarketingHeroProps}
      />

      {/* ── Marketing V2 ─────────────────────────────────────────
          30 seconds · 30fps · 900 frames · 1920×1080 (16:9)
          Evidential product proof film — brand film → conversion
      */}
      <Composition<MarketingV2Data>
        id="MarketingV2"
        component={MarketingV2}
        durationInFrames={V2_TOTAL_FRAMES}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={defaultMarketingV2Props}
      />
      {/* ── Marketing Hybrid ─────────────────────────────────────
          30.6 seconds · 30fps · 918 frames · 1920×1080 (16:9)
          Human Problem -> Real Product Action -> Remotion Proof -> Restraint -> Journal -> CTA
      */}
      <Composition<MarketingHybridData>
        id="MarketingHybrid"
        component={MarketingHybrid}
        durationInFrames={HYBRID_TOTAL_FRAMES}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={defaultMarketingHybridProps}
      />
      {/* ── Marketing Hybrid Vertical (9:16 Social) ───────────────
          30.6 seconds · 30fps · 918 frames · 1080×1920 (9:16)
          Reels / TikTok / Shorts Stacked Composition
      */}
      <Composition<MarketingHybridVerticalData>
        id="MarketingHybridVertical"
        component={MarketingHybridVertical}
        durationInFrames={HYBRID_TOTAL_FRAMES}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultMarketingHybridVerticalProps}
      />

      {/* ── Regime Performance (9:16 TikTok) ───────────────────────
          35.6 seconds · 30fps · 1067 frames · 1080×1920 (9:16)
          Evidence-based: 4,469 trades backtested (2021-2025)
      */}
      <Composition<RegimePerformanceData>
        id="RegimePerformance"
        component={RegimePerformance}
        durationInFrames={REGIME_TOTAL_FRAMES}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultRegimePerformanceProps}
      />

      {/* ── Hidden State (9:16 TikTok) ───────────────────────────────
          45 seconds · 30fps · 1350 frames · 1080×1920 (9:16)
          Timeline/Flow Diagram: 95% of transitions go through consolidation
      */}
      <Composition<HiddenStateData>
        id="HiddenState"
        component={HiddenState}
        durationInFrames={HIDDEN_TOTAL_FRAMES}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultHiddenStateProps}
      />

      {/* ── Template A: One chart, one question (9:16 TikTok) ───────
          30 seconds · 30fps · 900 frames · 1080×1920 (9:16)
          TikTok Constitution Template A
      */}
      <Composition<TemplateAData>
        id="TemplateA"
        component={TemplateA}
        durationInFrames={TEMPLATE_A_TOTAL_FRAMES}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultTemplateAProps}
      />

      {/* ── Limit vs Market Orders (9:16 TikTok) ─────────────────────
          60 seconds · 30fps · 1800 frames · 1080×1920 (9:16)
          Research: Limit orders outperform market orders by 52%
      */}
      <Composition<LimitVsMarketData>
        id="LimitVsMarket"
        component={LimitVsMarket}
        durationInFrames={LIMIT_VS_MARKET_TOTAL_FRAMES}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultLimitVsMarketProps}
      />
    </>
  );
};
