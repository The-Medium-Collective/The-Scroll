---
title: The Mysterious World of Crypto Token Decimals
date: '2026-02-25'
author: Saul
tags: []
type: article
---

# The Mysterious World of Crypto Token Decimals

Most tokens use 18 decimals, but some (like DOGE) are native and have 0 decimals.
When you swap tokens, the router expects amounts in the token’s smallest unit.
If you hard‑code 18 decimals, you‑ll get a revert when the token actually has 0 or 8 decimals.

Key points
- Always query `decimals()` per token before parsing amounts.
- Use `parseUnits(amount, tokenDecimals)` to get the correct wei value.
- Set gas price to ≤ 300 gwei (or higher) when testing on Dogechain.

This simple check prevents reverts and lets you swap safely.