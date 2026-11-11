# Path of Exile secondary illustration

The [dated snapshot](mercenaries_3_26_snapshot_2026-11-05.json) records a
small item list for the **regular Searing Exarch** encounter in Path of Exile 1,
**Mercenaries of Trarthus (3.26.0)**. Pokémon remains the primary case study.
The snapshot date, **2026-11-05 (Asia/Shanghai)**, is the date this reference
was compiled. It is not a date on which prices were observed, and the league
is historical. See the [official league announcement](https://webcdn.pathofexile.com/forum/view-thread/3789402/page/1).

| Item | Role | Community estimate per regular kill |
| --- | --- | ---: |
| Dawnbreaker | One possible item from the guaranteed unique pool | 63% |
| Dawnstrider | One possible item from the guaranteed unique pool | 35% |
| Dissolution of the Flesh | Rare target from the same pool | 2% |
| Incandescent Invitation | Entry item for another encounter | Not applicable |

The [pinned PoE Wiki revision](https://www.poewiki.net/index.php?title=The_Searing_Exarch&oldid=1636125#Drops)
reports these rounded estimates for 3.26.0 and cites 317 regular runs in total,
including a [public player report](https://www.reddit.com/r/pathofexile/comments/1mdirq6/i_ran_625_eaters_121_exarchs_1314_blueprint_wings/).
These are community estimates, not official odds or fresh measurements.
The first three items are alternatives in one drop pool, not independent rolls.
Do not mix regular and Uber runs or generalize the estimates across patches.

## Use alongside H5

The 2% target provides context for the 2% prior mean used by the existing
[synthetic H5 experiment](../../experiments/configs/H5_uncertain_odds.json).
For example, Beta(1, 49) starts at 2%, and its mean falls to 1% after 50
failures. This is an illustrative modeling choice: the prior's strength of
50 is not inferred from the wiki sample, and the synthetic H5 rewards and
timings are not measurements from Path of Exile.

This is a reference record, not a session JSON. All prices are intentionally
`null` (unobserved, not zero). If prices are added, use a single dated,
manually checked source for the same league and record its observation date,
URL, item variants and values in Chaos Orbs. The invitation belongs on the
cost side of a farming model, not among its rewards. Do not calculate
market-based rewards or profitability from this draft.

The snapshot uses published community reports only. It requires no gameplay,
bots, live market scraping, or game-server interaction.
