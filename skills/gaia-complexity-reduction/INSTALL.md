# Uso della skill di progetto

La skill e pensata per essere versionata in GAIA sotto:

```text
skills/gaia-complexity-reduction/
```

Non deve essere installata in `~/.hermes/skills` e non richiede modifiche a
`~/.hermes/config.yaml`.

## Caricamento

Il `AGENTS.md` di GAIA deve ordinare a Hermes di leggere:

```text
skills/gaia-complexity-reduction/SKILL.md
```

Anche i prompt `/goal` inclusi in `docs/code-quality/` contengono questa
istruzione esplicita. Hermes usa quindi il file come procedura di progetto,
senza registrarlo come slash command globale.

## Aggiornamento

La skill viene aggiornata tramite normali modifiche e review Git nello stesso
repository GAIA. Ogni modifica alla skill deve essere coerente con
`docs/code-quality/` e con il `AGENTS.md` autorevole.
