#!/bin/bash

# Скрипт настройки плана Porto
# Настраивает среду планирования для реализации функции Porto

set -e

# Получить текущую ветку и информацию о функции
BRANCH=$(git branch --show-current)

if [ -z "$BRANCH" ] || [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    echo "Ошибка: Не на ветке функции. Сначала используйте /specify."
    exit 1
fi

# Define paths
FEATURE_SPEC="$(pwd)/specs/${BRANCH}/spec.md"
IMPL_PLAN="$(pwd)/specs/${BRANCH}/plan.md"
SPECS_DIR="$(pwd)/specs/${BRANCH}"

# Check if spec exists
if [ ! -f "$FEATURE_SPEC" ]; then
    echo "Error: Feature spec not found at $FEATURE_SPEC"
    echo "Run /specify first to create the feature specification."
    exit 1
fi

# Create specs directory if it doesn't exist
mkdir -p "$SPECS_DIR"

# Copy Porto plan template if it doesn't exist
if [ ! -f "$IMPL_PLAN" ]; then
    if [ -f "spec-kit/templates/plan-template-porto.md" ]; then
        cp "spec-kit/templates/plan-template-porto.md" "$IMPL_PLAN"
        echo "Created implementation plan from Porto template"
    else
        echo "Warning: Porto plan template not found, creating basic plan"
        cat > "$IMPL_PLAN" << EOF
# Implementation Plan: $BRANCH (Porto)

**Branch**: \`$BRANCH\`
**Date**: $(date +%Y-%m-%d)
**Porto Container**: [AppSection/VendorSection].[ContainerName]

## Technical Context (Porto Stack)
**Framework**: Litestar 2.12+ (ASGI web framework)
**ORM**: Piccolo 1.22+ with SQLite (development) / PostgreSQL (production)
**DI Container**: Dishka 1.4+ (dependency injection)
**Observability**: Logfire 2.7+ (logging, tracing, monitoring)

## Porto Constitution Check
- [ ] Container placement justified
- [ ] Ship component reuse analyzed
- [ ] Porto principles compliance checked

## Phase 0: Porto Research & Analysis
[Research phase content]

## Phase 1: Porto Design & Contracts
[Design phase content]
EOF
    fi
fi

# Return JSON for script parsing
echo "{\"FEATURE_SPEC\":\"$FEATURE_SPEC\",\"IMPL_PLAN\":\"$IMPL_PLAN\",\"SPECS_DIR\":\"$SPECS_DIR\",\"BRANCH\":\"$BRANCH\"}"
