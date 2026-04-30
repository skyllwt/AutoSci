---
title: "Quasi-periodic oscillation"
aliases: ["QPO", "quasi-periodic oscillations"]
tags: [timing, neutron-star, accretion, magnetar, astrophysics]
maturity: stable
key_papers: ["[[very-high-frequency-oscillations-main-peak]]"]
first_introduced: "1985"
date_updated: 2026-04-30
related_concepts: ["[[magnetar-giant-flare]]"]
---

## Definition

A quasi-periodic oscillation (QPO) is a peak of finite width in the power spectral density of a time-variable astrophysical signal — narrow enough to be distinguished from broadband noise but broader (lower coherence Q) than a strictly periodic signal. QPOs reveal characteristic timescales of the emitting system (magnetospheric, accretion-disk, or stellar oscillations) without implying perfect periodicity.

## Intuition

If a system has a preferred timescale — Alfvén crossing time, Keplerian orbital frequency, stellar oscillation mode — but the source of variability is intermittent or driven by a stochastic process, the resulting power spectrum shows a broad bump rather than a delta-function peak. The centroid frequency and width together encode the underlying physics and the damping/driving regime.

## Formal notation

A QPO is typically characterized by centroid frequency f_0, full-width-at-half-maximum delta_f, quality factor Q = f_0 / delta_f, and statistical significance (often expressed as a chance probability under a noise model such as Leahy-normalized power-spectrum statistics or Z_m^2 Rayleigh-style statistics on event arrival times).

## Variants

- **Low-frequency QPOs** — sub-100 Hz; commonly observed in the tails of magnetar giant flares, attributed to global crustal or magnetospheric oscillations.
- **High-frequency QPOs (kHz QPOs)** — ~500 Hz to several kHz; previously seen in the tail phase of giant flares and in the X-ray emission of accreting neutron stars.
- **Main-peak high-frequency QPOs** — kHz QPOs detected during the burst-peak phase itself (rather than the tail), as in GRB 200415A.

## Comparison

QPOs differ from coherent pulsations (perfect periodicity, Q -> infinity) and from broadband red/white noise (no preferred frequency). The line between a "narrow QPO" and a "coherent pulsation" is set by Q and by the chosen significance threshold.

## When to use

When characterizing timing structure of compact-object emission whose power spectrum shows preferred frequencies — magnetar flares, accreting neutron-star X-ray binaries, accreting black-hole binaries.

## Known limitations

- Statistical significance of QPOs is sensitive to the assumed noise model and the search-window choice; published detections at low SNR have been contested.
- Mapping QPO frequencies to specific physical modes (crustal shear, Alfvén, disk-orbital) requires additional modeling and is rarely unique.

## Open problems

- Whether kHz QPOs in magnetar giant flares originate from magnetospheric Alfvén-wave reconnection or from (magneto-)elastic crustal oscillations — both interpretations are viable for current data.
- How to combine QPO timing measurements across multiple detectors and energy bands to constrain neutron-star equation of state.

## Key papers

- [[very-high-frequency-oscillations-main-peak]] — establishes that significant kHz QPOs are present during the main burst peak (not only the tail) of a magnetar giant flare.

## My understanding

QPOs are a primary observational handle on otherwise inaccessible compact-object physics. Their interpretive power is strong when multiple frequencies are detected together (allowing identification of harmonics or mode families) and when the timing detection is co-located in time with spectral features (as in this paper, where the QPOs disappear together with the rise of the non-thermal component).
