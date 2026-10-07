# Failure taxonomy for recall-as-of-qwen3-2026-10-04T1415Z

A miss: the right rule (A1) is not in the top 5. One category each,
by the rule in rb_errata/taxonomy.py; no model.

| stratum | below-cutoff | card-not-in-corpus | rule-only | unclassified | misses |
|---|---|---|---|---|---|
| expert-ruling | 37 | 21 | 2 | 0 | 60 |
| expert-ruling-faq | 3 | 2 | 0 | 0 | 5 |
| version-change | 8 | 0 | 0 | 4 | 12 |
| **all** | 48 | 23 | 2 | 4 | 77 |

below-cutoff ranks: 27 of 48 at rank 6 to 10.

## Every miss

| question | stratum | category | rank |
|---|---|---|---|
| r-abandoned-hall-countered-spell | expert-ruling | below-cutoff | 6 |
| r-abandoned-hall-movement-eligibility | expert-ruling | below-cutoff | 11 |
| r-abilities-source-removal | expert-ruling | below-cutoff | 16 |
| r-akshan-mischievous-aurora-timing | expert-ruling | below-cutoff | 13 |
| r-alpha-strike-illegal-enemy-target | expert-ruling | below-cutoff | 8 |
| r-alpha-strike-illegal-friendly-target | expert-ruling | below-cutoff | 7 |
| r-alpha-strike-targeting | expert-ruling | below-cutoff | 7 |
| r-ambush-ambush-showdown-focus | expert-ruling | below-cutoff | 9 |
| r-astral-heron-removed-in-response | expert-ruling | below-cutoff | 18 |
| r-bone-skewer-stun-targeting | expert-ruling | below-cutoff | 9 |
| r-chain-and-priority-partial-chain-reactions | expert-ruling | below-cutoff | 10 |
| r-chain-and-priority-unit-play-reactions | expert-ruling | below-cutoff | 10 |
| r-diana-lunari-ability-finalization-cost | expert-ruling | below-cutoff | 6 |
| r-diana-lunari-trigger-resolution-order | expert-ruling | below-cutoff | 6 |
| r-emperors-dais-ability-finalization-cost | expert-ruling | below-cutoff | 11 |
| r-emperors-dais-source-location | expert-ruling | below-cutoff | 17 |
| r-endless-riches-draw-phase-duration | expert-ruling | below-cutoff | 13 |
| r-equipment-equipment-after-death | expert-ruling | below-cutoff | 12 |
| r-glasc-mixologist-deathknell-combat-result | expert-ruling | below-cutoff | 9 |
| r-heedless-resurrection-self-resurrection | expert-ruling | below-cutoff | 14 |
| r-hidden-blade-draw-if-not-killed | expert-ruling-faq | below-cutoff | 9 |
| r-irelia-fervent-targeting-before-counter | expert-ruling | below-cutoff | 8 |
| r-irresistible-faefolk-removed-in-response | expert-ruling | below-cutoff | 7 |
| r-khazix-mutating-horror-trigger-per-combat | expert-ruling | below-cutoff | 7 |
| r-khazix-mutating-horror-unit-play-in-response | expert-ruling | below-cutoff | 6 |
| r-movement-entering-board | expert-ruling | below-cutoff | 12 |
| r-playing-cards-play-process | expert-ruling | below-cutoff | 11 |
| r-promising-future-brynhir-thundersong | expert-ruling | below-cutoff | 13 |
| r-promising-future-resolution | expert-ruling | below-cutoff | 11 |
| r-rebuttal-play-trigger-controller | expert-ruling-faq | below-cutoff | 6 |
| r-sacrifice-cost-reaction-window | expert-ruling | below-cutoff | 8 |
| r-switcheroo-existing-modifiers | expert-ruling | below-cutoff | 8 |
| r-switcheroo-might-swap | expert-ruling | below-cutoff | 14 |
| r-switcheroo-negative-might | expert-ruling | below-cutoff | 11 |
| r-targeting-ignored-negated-instructions | expert-ruling-faq | below-cutoff | 11 |
| r-temporal-breach-prevented-replay | expert-ruling | below-cutoff | 20 |
| r-temporal-breach-replayed-unit-state | expert-ruling | below-cutoff | 7 |
| r-temporal-breach-score-on-opponents-turn | expert-ruling | below-cutoff | 9 |
| r-temporal-breach-token-unit | expert-ruling | below-cutoff | 10 |
| r-vex-apathetic-stun-targeting | expert-ruling | below-cutoff | 10 |
| v-control-without-contest-current | version-change | below-cutoff | 11 |
| v-control-without-contest-v1.3 | version-change | below-cutoff | 9 |
| v-draw-phase-current | version-change | below-cutoff | 16 |
| v-draw-phase-v1.3 | version-change | below-cutoff | 17 |
| v-gear-to-battlefield-v1.2 | version-change | below-cutoff | 8 |
| v-legend-leave-zone-v1.3 | version-change | below-cutoff | 8 |
| v-legion-countered-spell-v1.3 | version-change | below-cutoff | 8 |
| v-replacement-from-triggered-current | version-change | below-cutoff | 11 |
| r-akshan-mischievous-dual-akshan-control | expert-ruling | card-not-in-corpus | >20 |
| r-aphelios-exalted-equipment-copy-effects | expert-ruling-faq | card-not-in-corpus | >20 |
| r-arcane-shift-replay-at-same-battlefield | expert-ruling | card-not-in-corpus | >20 |
| r-azir-sovereign-attack-trigger-without-azir | expert-ruling | card-not-in-corpus | >20 |
| r-baron-nashor-baron-pit-showdown | expert-ruling | card-not-in-corpus | >20 |
| r-baron-nashor-warden-play-lock | expert-ruling | card-not-in-corpus | >20 |
| r-brynhir-thundersong-existing-cards | expert-ruling | card-not-in-corpus | >20 |
| r-call-to-battle-same-battlefield-destination | expert-ruling | card-not-in-corpus | >20 |
| r-consuming-curse-self-count | expert-ruling | card-not-in-corpus | >20 |
| r-elder-dragon-zero-target-finalization | expert-ruling | card-not-in-corpus | >20 |
| r-elder-dragon-zhonyas-target-timing | expert-ruling | card-not-in-corpus | >20 |
| r-endless-riches-recycle-destination | expert-ruling | card-not-in-corpus | >20 |
| r-fallen-feline-existing-spells | expert-ruling | card-not-in-corpus | >20 |
| r-gangplank-naval-switcheroo-might-reduction | expert-ruling-faq | card-not-in-corpus | >20 |
| r-irelia-fervent-blade-dancer | expert-ruling | card-not-in-corpus | >20 |
| r-irresistible-faefolk-playing-vs-moving | expert-ruling | card-not-in-corpus | >20 |
| r-kennen-storm-of-shuriken-minefield-flow | expert-ruling | card-not-in-corpus | >20 |
| r-lux-crownguard-hard-bargain-payment | expert-ruling | card-not-in-corpus | >20 |
| r-promising-future-disarming-rake | expert-ruling | card-not-in-corpus | >20 |
| r-promising-future-ravenbloom-prefect | expert-ruling | card-not-in-corpus | >20 |
| r-rebuttal-power-payment-timing | expert-ruling | card-not-in-corpus | >20 |
| r-smite-death-replacement-effects | expert-ruling | card-not-in-corpus | >20 |
| r-switcheroo-later-modifier-changes | expert-ruling | card-not-in-corpus | >20 |
| r-playing-cards-playing-from-trash | expert-ruling | rule-only | >20 |
| r-targeting-target-restrictions | expert-ruling | rule-only | >20 |
| v-attached-gear-moves-current | version-change | unclassified | >20 |
| v-attached-gear-moves-v1.3 | version-change | unclassified | >20 |
| v-showdown-or-combat-first-current | version-change | unclassified | >20 |
| v-showdown-or-combat-first-v1.3 | version-change | unclassified | >20 |
