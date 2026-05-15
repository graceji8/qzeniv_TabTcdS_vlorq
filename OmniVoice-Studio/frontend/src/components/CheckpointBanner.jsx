import React from 'react';
import { CheckCircle, ArrowRight, X, Sparkles, Languages, Mic } from 'lucide-react';
import { Button } from '../ui';
import './Misc.css';

/**
 * Phase 4.3 — between-stage checkpoint banner.
 *
 * The dub pipeline has three natural review points (post-ASR, post-translate,
 * post-generate). Each one is a chance for the user to spot a mistake before
 * it compounds into the next stage. This banner makes that review window
 * explicit instead of silently leaving the user on the segment editor with
 * no cue about what to do next.
 *
 * Render it above the segment table. Pass `onContinue` to advance the
 * pipeline directly from the banner's CTA (translate, generate, etc).
 */

const STAGE_CONFIG = {
  asr: {
    icon: Mic,
    accent: '#b8bb26',
    title: 'Transcripts ready',
    cta: 'Translate',
    ctaIcon: Languages,
    hint: 'Fix any ASR errors now — tight diction saves TTS attempts later.',
  },
  translate: {
    icon: Languages,
    accent: '#83a598',
    title: 'Translations ready',
    cta: 'Generate dub',
    ctaIcon: Sparkles,
    hint: 'Skim the target text. Over-length lines get speed-boosted; you can also edit directly.',
  },
  done: {
    icon: CheckCircle,
    accent: '#8ec07c',
    title: 'Dub complete',
    cta: null,
    hint: 'Review timing and sync ratios. Tweak any line and hit "Regen changed" for a fast partial redo.',
  },
};

export default function CheckpointBanner({ stage, count, onContinue, onDismiss, continueLoading }) {
  const cfg = STAGE_CONFIG[stage];
  if (!cfg) return null;

  const Icon = cfg.icon;
  const CtaIcon = cfg.ctaIcon;

  return (
    <div
      className="checkpoint-banner ckpt-banner"
      style={{ borderLeft: `2px solid ${cfg.accent}` }}
      role="status"
    >
      <Icon size={14} color={cfg.accent} className="ckpt-icon" />
      <div className="ckpt-body">
        <div className="ckpt-head">
          <span className="ckpt-title">
            {cfg.title}
          </span>
          {typeof count === 'number' && (
            <span className="ckpt-count">
              {count} segment{count === 1 ? '' : 's'}
            </span>
          )}
        </div>
        <span className="ckpt-hint">
          {cfg.hint}
        </span>
      </div>
      {cfg.cta && onContinue && (
        <Button
          variant="subtle"
          size="sm"
          onClick={onContinue}
          loading={continueLoading}
          leading={CtaIcon ? <CtaIcon size={10} /> : null}
          trailing={<ArrowRight size={10} />}
        >
          {cfg.cta}
        </Button>
      )}
      {onDismiss && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onDismiss}
          title="Dismiss — won't reappear for this stage until reload"
          iconSize="sm"
        >
          <X size={10} />
        </Button>
      )}
    </div>
  );
}
