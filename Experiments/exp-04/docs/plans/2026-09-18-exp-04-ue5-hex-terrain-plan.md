# exp-04 UE5 Hex Terrain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A UE5.8 C++ project that plays with hilly procedural terrain, a flat 2D hex grid draped onto that terrain, an overhead camera that pans and zooms and tilts as it zooms, and a highlight on the tile under the mouse.

**Architecture:** One runtime C++ module, `MuraBito`. Pure math (`FHexGrid`, `FTerrainHeight`, `MeshBuilders`, `CameraMath`) has no UObject and is covered by automation tests. Thin actors (`ATerrain`, `AHexOverlay`, `ACameraRig`, `AInputController`, `AWorldBuilder`) wire that math into the engine. At startup `AWorldBuilder`, the global game mode, spawns everything into the engine's empty `/Engine/Maps/Entry` map, so the repo holds no binary assets.

**Tech Stack:** Unreal Engine 5.8.2 installed build (Linux, bundled clang), C++, the ProceduralMeshComponent and EnhancedInput plugins, and UE Automation tests run headless through `UnrealEditor-Cmd`.

**Spec:** `Experiments/exp-04/docs/specs/2026-09-18-exp-04-ue5-hex-terrain-design.md`

## Global Constraints

- Public MIT repo: **copy nothing from the engine tree** into the repo. Write all files fresh here, and never paste Epic copyright headers. Reading engine headers and source to check an API is fine.
- **No binary assets:** no `.uasset` or `.umap`, and no Git LFS. Everything is made in C++ at runtime.
- **Naming:** plain names that say what each class does. Keep UE's required type prefixes (`A`, `F`, `U`), but the names after them are ours, e.g. `ACameraRig`, not a "…Pawn". Code, comments and docs never name a game that inspired the project.
- Only what's needed to build, run and develop goes in git. `Binaries/`, `Intermediate/`, `Saved/`, `DerivedDataCache/` and generated IDE files are ignored.
- `UE_ROOT` defaults to `/home/lexa/DevProjects/_GameDev/_GameEngines/UnrealEngine/5.8.2` and can be overridden from the environment.
- The experiment root is `EXP=/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04/Experiments/exp-04`, on branch `worktree-exp-04` of the worktree `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04`. **Always use absolute paths. Every git command is `git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04 …`.** Never touch the main checkout at `/home/lexa/DevProjects/_GameDev/MuraBito`. Before each commit, run `git -C <worktree> rev-parse --abbrev-ref HEAD` and check that it prints `worktree-exp-04`.
- **Never kill, signal, or otherwise interfere with any process you did not start yourself**, above all an `UnrealEditor` the user has open. If a running process blocks a build or test (for example `build.sh` refusing because an editor is running), stop and report BLOCKED, naming the process. The user closes it. Don't work around it.
- Use `rg` (ripgrep), not `grep`, in scripts and commands. In `rg`, `-E` means encoding, so don't use it for regex.
- Commit messages start with `exp-04: ` and end with the trailer `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- The UE coordinate convention in this project: X is forward (up the screen at camera yaw 0), Y is right, Z is up, and the unit is cm.
- **Triangle winding:** the engine's own up-facing grid (`UKismetProceduralMeshLibrary::CreateGridMeshWelded`) emits triangles `(A, B, C)` with `CrossProduct(B - A, C - A).Z < 0`. So a triangle faces **up** (+Z) when that cross product's Z is **negative**. All mesh builders enforce this, and the tests check it.

## File map

```
Experiments/exp-04/
├─ .gitignore
├─ MuraBito.uproject
├─ Config/DefaultEngine.ini, DefaultGame.ini, DefaultInput.ini
├─ scripts/env.sh, build.sh, editor.sh, game.sh, test.sh
└─ Source/
   ├─ MuraBito.Target.cs, MuraBitoEditor.Target.cs
   └─ MuraBito/
      ├─ MuraBito.Build.cs
      ├─ Public/
      │  ├─ MuraBitoLog.h        log category LogMuraBito
      │  ├─ HexGrid.h            FHex, FHexGrid              (Task 2)
      │  ├─ TerrainHeight.h      FTerrainHeight              (Task 3)
      │  ├─ MeshData.h           FMeshData                   (Task 4)
      │  ├─ MeshBuilders.h       FDrapeParams, MeshBuilders:: (Task 4)
      │  ├─ CameraMath.h         FZoomRange, CameraMath::    (Task 5)
      │  ├─ Materials.h          Materials::                 (Task 6)
      │  ├─ Terrain.h            ATerrain                    (Task 6)
      │  ├─ HexOverlay.h         AHexOverlay                 (Task 6)
      │  ├─ CameraRig.h          ACameraRig                  (Task 7)
      │  ├─ InputController.h    AInputController            (Task 7)
      │  └─ WorldBuilder.h       AWorldBuilder               (Task 7)
      └─ Private/  (matching .cpp files, plus MuraBito.cpp)
         └─ Tests/ SmokeTest.cpp (Task 1, deleted in Task 2), HexGridTests.cpp,
                   TerrainHeightTests.cpp, MeshBuildersTests.cpp, CameraMathTests.cpp
```

The manifest entry in `Experiments/manifest.md` is added in Task 8.

## Running things

- **Build:** `$EXP/scripts/build.sh`. The first build takes several minutes. If the editor is open, close it first, or the build may clash with Live Coding.
- **Tests:** `$EXP/scripts/test.sh [Filter]` builds, then runs every automation test whose path starts with `Filter` (default `MuraBito`). It exits 0 only if at least one test ran and none failed. Its first run is slow (1–3 minutes) because of engine startup.

---

### Task 1: Project scaffold, scripts and test harness

**Files:**
- Create: `$EXP/.gitignore`, `$EXP/MuraBito.uproject`, `$EXP/Config/DefaultEngine.ini`, `$EXP/Config/DefaultGame.ini`, `$EXP/Config/DefaultInput.ini`
- Create: `$EXP/Source/MuraBito.Target.cs`, `$EXP/Source/MuraBitoEditor.Target.cs`, `$EXP/Source/MuraBito/MuraBito.Build.cs`
- Create: `$EXP/Source/MuraBito/Public/MuraBitoLog.h`, `$EXP/Source/MuraBito/Private/MuraBito.cpp`
- Create: `$EXP/scripts/env.sh`, `build.sh`, `editor.sh`, `game.sh`, `test.sh` (all `chmod +x`)
- Test: `$EXP/Source/MuraBito/Private/Tests/SmokeTest.cpp`

**Interfaces:**
- Produces: module `MuraBito` (export macro `MURABITO_API`), log category `LogMuraBito`, and the scripts above. The test path prefix is `MuraBito.`.

- [ ] **Step 1: Write `.gitignore`**

```gitignore
# Unreal build outputs, caches and per-user state
Binaries/
Intermediate/
Saved/
DerivedDataCache/

# Generated IDE / project files
.vs/
*.code-workspace
/Makefile
/CMakeLists.txt
/*.pro
/*.pri
/*.kdev4
/.kdev4/
/compile_commands.json
/.clangd
```

- [ ] **Step 2: Write `MuraBito.uproject`**

```json
{
	"FileVersion": 3,
	"EngineAssociation": "5.8",
	"Category": "",
	"Description": "MuraBito exp-04: procedural hex terrain and overhead camera",
	"Modules": [
		{
			"Name": "MuraBito",
			"Type": "Runtime",
			"LoadingPhase": "Default"
		}
	],
	"Plugins": [
		{ "Name": "ProceduralMeshComponent", "Enabled": true },
		{ "Name": "EnhancedInput", "Enabled": true }
	]
}
```

- [ ] **Step 3: Write the config files**

`Config/DefaultEngine.ini`:

```ini
[/Script/EngineSettings.GameMapsSettings]
; The engine's own empty map. The world is built in C++ at startup, so the
; project has no level of its own. Don't save this map from the editor.
GameDefaultMap=/Engine/Maps/Entry
EditorStartupMap=/Engine/Maps/Entry
GlobalDefaultGameMode=/Script/MuraBito.WorldBuilder

[/Script/Engine.RendererSettings]
r.AllowStaticLighting=False

[/Script/LinuxTargetPlatform.LinuxTargetSettings]
-TargetedRHIs=SF_VULKAN_SM5
+TargetedRHIs=SF_VULKAN_SM6
```

`Config/DefaultGame.ini`:

```ini
[/Script/EngineSettings.GeneralProjectSettings]
ProjectID=0D26B12ED76447ABB289C19A961CCE67
ProjectName=MuraBito
ProjectVersion=0.0.1
```

`Config/DefaultInput.ini`:

```ini
[/Script/Engine.InputSettings]
DefaultPlayerInputClass=/Script/EnhancedInput.EnhancedPlayerInput
DefaultInputComponentClass=/Script/EnhancedInput.EnhancedInputComponent
```

- [ ] **Step 4: Write the targets and module rules**

`Source/MuraBito.Target.cs`:

```csharp
using UnrealBuildTool;

public class MuraBitoTarget : TargetRules
{
	public MuraBitoTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("MuraBito");
	}
}
```

`Source/MuraBitoEditor.Target.cs`:

```csharp
using UnrealBuildTool;

public class MuraBitoEditorTarget : TargetRules
{
	public MuraBitoEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("MuraBito");
	}
}
```

`Source/MuraBito/MuraBito.Build.cs`:

```csharp
using UnrealBuildTool;

public class MuraBito : ModuleRules
{
	public MuraBito(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "ProceduralMeshComponent",
		});
	}
}
```

- [ ] **Step 5: Write the module and log category**

`Source/MuraBito/Public/MuraBitoLog.h`:

```cpp
#pragma once

#include "CoreMinimal.h"

MURABITO_API DECLARE_LOG_CATEGORY_EXTERN(LogMuraBito, Log, All);
```

`Source/MuraBito/Private/MuraBito.cpp`:

```cpp
#include "MuraBitoLog.h"
#include "Modules/ModuleManager.h"

DEFINE_LOG_CATEGORY(LogMuraBito);

IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, MuraBito, "MuraBito");
```

- [ ] **Step 6: Write the scripts**

`scripts/env.sh`:

```bash
#!/usr/bin/env bash
# Shared settings, sourced by the other scripts.
# Set UE_ROOT to use a different Unreal Engine 5.8 install.
set -euo pipefail

UE_ROOT="${UE_ROOT:-/home/lexa/DevProjects/_GameDev/_GameEngines/UnrealEngine/5.8.2}"
EXP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="$EXP_DIR/MuraBito.uproject"
EDITOR="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
EDITOR_CMD="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd"
BUILD_SH="$UE_ROOT/Engine/Build/BatchFiles/Linux/Build.sh"

for f in "$EDITOR" "$EDITOR_CMD" "$BUILD_SH"; do
  if [[ ! -x "$f" ]]; then
    echo "error: no Unreal Engine install at UE_ROOT=$UE_ROOT (missing $f)" >&2
    exit 1
  fi
done

# Refuse to build while any Unreal Editor is running. A running editor makes rebuilt modules
# load under a new hot-reload name, so tests would silently run stale code. Close the editor
# yourself; these scripts never stop it for you.
require_no_running_editor() {
  local running
  running=$(pgrep -a -f '/UnrealEditor(-Cmd)?( |$)' || true)
  if [[ -n "$running" ]]; then
    echo "error: an Unreal Editor is running. Close it, then retry:" >&2
    echo "$running" >&2
    exit 1
  fi
}
```

`scripts/build.sh`:

```bash
#!/usr/bin/env bash
# Build the editor target (Development, Linux). Extra args go to UnrealBuildTool.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
require_no_running_editor
"$BUILD_SH" MuraBitoEditor Linux Development -Project="$PROJECT" -WaitMutex "$@"
```

`scripts/editor.sh`:

```bash
#!/usr/bin/env bash
# Open the project in the editor. Press Play to run the world.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
exec "$EDITOR" "$PROJECT" "$@"
```

`scripts/game.sh`:

```bash
#!/usr/bin/env bash
# Run standalone in a window. Pass -Seed=N for a different terrain.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
exec "$EDITOR" "$PROJECT" -game -windowed -ResX=1600 -ResY=900 -log "$@"
```

`scripts/test.sh`:

```bash
#!/usr/bin/env bash
# Build, then run automation tests headless. Usage: test.sh [TestPathPrefix]
# Exits 0 only if at least one test ran and none failed.
source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
FILTER="${1:-MuraBito}"

"$(dirname "${BASH_SOURCE[0]}")/build.sh"

LOG_DIR="$EXP_DIR/Saved/TestLogs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/test-$(date +%Y%m%d-%H%M%S).log"

set +e
"$EDITOR_CMD" "$PROJECT" \
  -ExecCmds="Automation RunTests $FILTER" \
  -TestExit="Automation Test Queue Empty" \
  -unattended -nullrhi -nosplash -nosound -stdout -FullStdOutLogOutput \
  > "$LOG" 2>&1
CODE=$?
set -e

rg --no-line-number "Test Completed\. Result=" "$LOG" || true
PASSED=$(rg -c "Test Completed\. Result=\{Success\}" "$LOG" || true)
FAILED=$(rg -c "Test Completed\. Result=\{Fail" "$LOG" || true)
PASSED=${PASSED:-0}
FAILED=${FAILED:-0}

echo "passed: $PASSED  failed: $FAILED  editor exit code: $CODE"
echo "log: $LOG"
if [[ "$FAILED" -ne 0 || "$PASSED" -eq 0 || "$CODE" -ne 0 ]]; then
  rg --no-line-number "Error: |Expected " "$LOG" | head -40 || true
  echo "TESTS FAILED"
  exit 1
fi
echo "TESTS PASSED"
```

Run: `chmod +x $EXP/scripts/*.sh`

- [ ] **Step 7: Write a deliberately failing smoke test**

This checks that the harness really reports failures. `Source/MuraBito/Private/Tests/SmokeTest.cpp`:

```cpp
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSmokeTest, "MuraBito.Smoke",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter)

bool FSmokeTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("one plus one"), 1 + 1, 3);
	return true;
}

#endif
```

- [ ] **Step 8: Build and run tests, expecting FAIL**

Run: `$EXP/scripts/test.sh`
Expected: the build succeeds, then the output shows `Result={Fail}` for `MuraBito.Smoke`, `failed: 1`, `TESTS FAILED`, and exit code 1.

If the log format differs from `Test Completed. Result={Success|Fail}`, open the log file it printed, find the real per-test result line, and fix the `rg` patterns in `test.sh` to match it. The script must be able to tell pass from fail. If the editor doesn't exit on its own, check the `-TestExit` spelling against the log.

- [ ] **Step 9: Make the smoke test pass**

Change `3` to `2` in `SmokeTest.cpp`.

Run: `$EXP/scripts/test.sh`
Expected: `passed: 1  failed: 0`, `TESTS PASSED`, exit 0.

Also run: `$EXP/scripts/test.sh MuraBito.DoesNotExist`
Expected: `passed: 0`, `TESTS FAILED`, exit 1. A filter that matches nothing must not count as a pass.

Then check the running-editor guard with a stand-in process you start yourself (it only borrows the name):

```bash
bash -c 'exec -a /tmp/fake/UnrealEditor sleep 60' &
FAKE=$!
sleep 1
$EXP/scripts/build.sh; echo "exit: $?"
kill $FAKE   # your own stand-in only
```

Expected: `error: an Unreal Editor is running…`, a line listing the stand-in `sleep`, and `exit: 1`.

- [ ] **Step 10: Check git sees only source files, then commit**

Run: `git -C /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04 status --porcelain`
Expected: only `.gitignore`, `MuraBito.uproject`, `Config/`, `Source/` and `scripts/` under `Experiments/exp-04/`. No `Binaries/`, `Intermediate/`, `Saved/` or `DerivedDataCache/`.

```bash
W=/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04
git -C $W rev-parse --abbrev-ref HEAD   # must print worktree-exp-04
git -C $W add Experiments/exp-04
git -C $W commit -m "exp-04: UE5 project scaffold, scripts and automation test harness

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `FHexGrid`: pointy-top axial hex math

**Files:**
- Create: `$EXP/Source/MuraBito/Public/HexGrid.h`, `$EXP/Source/MuraBito/Private/HexGrid.cpp`
- Test: `$EXP/Source/MuraBito/Private/Tests/HexGridTests.cpp`
- Delete: `$EXP/Source/MuraBito/Private/Tests/SmokeTest.cpp` (the real tests take its place)

**Interfaces:**
- Produces:
  - `struct FHex { int32 Q, R; FHex(); FHex(int32, int32); int32 S() const; ==, !=, +; GetTypeHash }`
  - `struct FHexGrid { float TileSize; int32 Radius; FHexGrid(float InTileSize, int32 InRadius); FVector2D HexToXY(const FHex&) const; FHex XYToHex(const FVector2D&) const; TStaticArray<FVector2D, 6> Corners(const FHex&) const; static TStaticArray<FHex, 6> Neighbors(const FHex&); static int32 Distance(const FHex&, const FHex&); bool Contains(const FHex&) const; TArray<FHex> Tiles() const; int32 NumTiles() const; FBox2D Bounds() const; }`
  - `Corners(H)[i]` sits at angle `60*i - 30` degrees from the tile center, and edge `i` runs from corner `i` to corner `(i+1)%6`. The side length equals `TileSize`.

- [ ] **Step 1: Write the failing tests**

`Source/MuraBito/Private/Tests/HexGridTests.cpp`:

```cpp
#include "Misc/AutomationTest.h"
#include "HexGrid.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	constexpr EAutomationTestFlags HexTestFlags =
		EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FHexGridRoundTripTest, "MuraBito.HexGrid.RoundTrip", HexTestFlags)
bool FHexGridRoundTripTest::RunTest(const FString& Parameters)
{
	const FHexGrid Grid(300.f, 12);
	for (const FHex& Hex : Grid.Tiles())
	{
		const FHex Back = Grid.XYToHex(Grid.HexToXY(Hex));
		TestTrue(FString::Printf(TEXT("round trip (%d,%d)"), Hex.Q, Hex.R), Back == Hex);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FHexGridOriginTest, "MuraBito.HexGrid.Origin", HexTestFlags)
bool FHexGridOriginTest::RunTest(const FString& Parameters)
{
	const FHexGrid Grid(300.f, 12);
	TestTrue(TEXT("origin tile at 0,0"), Grid.HexToXY(FHex(0, 0)).Equals(FVector2D::ZeroVector, 0.001));
	// Pointy-top: moving +Q steps along +X by sqrt(3)*size, +R steps by (sqrt(3)/2*size, 1.5*size).
	TestTrue(TEXT("+Q"), Grid.HexToXY(FHex(1, 0)).Equals(FVector2D(FMath::Sqrt(3.f) * 300.f, 0.f), 0.01));
	TestTrue(TEXT("+R"), Grid.HexToXY(FHex(0, 1)).Equals(FVector2D(FMath::Sqrt(3.f) * 150.f, 450.f), 0.01));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FHexGridInsideEdgesTest, "MuraBito.HexGrid.PointsInsideTile", HexTestFlags)
bool FHexGridInsideEdgesTest::RunTest(const FString& Parameters)
{
	const FHexGrid Grid(300.f, 12);
	const FHex Samples[] = { FHex(0, 0), FHex(3, -2), FHex(-5, 7), FHex(12, -12), FHex(-12, 0) };
	for (const FHex& Hex : Samples)
	{
		const FVector2D Center = Grid.HexToXY(Hex);
		for (const FVector2D& Corner : Grid.Corners(Hex))
		{
			// 95% of the way to each corner is still inside the tile.
			const FVector2D P = FMath::Lerp(Center, Corner, 0.95);
			TestTrue(FString::Printf(TEXT("near-corner point in (%d,%d)"), Hex.Q, Hex.R), Grid.XYToHex(P) == Hex);
		}
		const TStaticArray<FVector2D, 6> C = Grid.Corners(Hex);
		for (int32 i = 0; i < 6; ++i)
		{
			// 95% of the way to each edge midpoint is still inside the tile.
			const FVector2D Mid = (C[i] + C[(i + 1) % 6]) * 0.5;
			const FVector2D P = FMath::Lerp(Center, Mid, 0.95);
			TestTrue(FString::Printf(TEXT("near-edge point in (%d,%d)"), Hex.Q, Hex.R), Grid.XYToHex(P) == Hex);
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FHexGridCornersTest, "MuraBito.HexGrid.Corners", HexTestFlags)
bool FHexGridCornersTest::RunTest(const FString& Parameters)
{
	const FHexGrid Grid(300.f, 12);
	const FHex Hex(2, -1);
	const FVector2D Center = Grid.HexToXY(Hex);
	const TStaticArray<FVector2D, 6> C = Grid.Corners(Hex);
	for (int32 i = 0; i < 6; ++i)
	{
		TestEqual(TEXT("corner radius"), FVector2D::Distance(Center, C[i]), 300.0, 0.01);
		TestEqual(TEXT("side length"), FVector2D::Distance(C[i], C[(i + 1) % 6]), 300.0, 0.01);
	}
	// Corner 0 is at -30 degrees.
	const FVector2D Expected0 = Center + 300.0 * FVector2D(FMath::Cos(FMath::DegreesToRadians(-30.0)), FMath::Sin(FMath::DegreesToRadians(-30.0)));
	TestTrue(TEXT("corner 0 angle"), C[0].Equals(Expected0, 0.01));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FHexGridNeighborsTest, "MuraBito.HexGrid.Neighbors", HexTestFlags)
bool FHexGridNeighborsTest::RunTest(const FString& Parameters)
{
	const FHexGrid Grid(300.f, 12);
	const FHex Hex(1, 2);
	const TStaticArray<FHex, 6> N = FHexGrid::Neighbors(Hex);
	TSet<FHex> Unique;
	for (const FHex& Other : N)
	{
		Unique.Add(Other);
		TestEqual(TEXT("neighbor at distance 1"), FHexGrid::Distance(Hex, Other), 1);
		TestEqual(TEXT("neighbor center spacing"),
			FVector2D::Distance(Grid.HexToXY(Hex), Grid.HexToXY(Other)), FMath::Sqrt(3.0) * 300.0, 0.01);
	}
	TestEqual(TEXT("six distinct neighbors"), Unique.Num(), 6);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FHexGridMapTest, "MuraBito.HexGrid.Map", HexTestFlags)
bool FHexGridMapTest::RunTest(const FString& Parameters)
{
	for (int32 R : { 0, 1, 2, 12 })
	{
		const FHexGrid Grid(300.f, R);
		const int32 Expected = 3 * R * R + 3 * R + 1;
		TestEqual(FString::Printf(TEXT("NumTiles R=%d"), R), Grid.NumTiles(), Expected);
		TestEqual(FString::Printf(TEXT("Tiles().Num R=%d"), R), Grid.Tiles().Num(), Expected);
		TSet<FHex> Unique(Grid.Tiles());
		TestEqual(TEXT("tiles are unique"), Unique.Num(), Expected);
	}
	const FHexGrid Grid(300.f, 12);
	TestTrue(TEXT("edge tile inside"), Grid.Contains(FHex(12, -12)));
	TestTrue(TEXT("edge tile inside"), Grid.Contains(FHex(0, -12)));
	TestFalse(TEXT("just outside"), Grid.Contains(FHex(13, -12)));
	TestFalse(TEXT("just outside"), Grid.Contains(FHex(7, 6)));
	TestTrue(TEXT("inside"), Grid.Contains(FHex(6, 6)));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FHexGridBoundsTest, "MuraBito.HexGrid.Bounds", HexTestFlags)
bool FHexGridBoundsTest::RunTest(const FString& Parameters)
{
	const FHexGrid Grid(300.f, 12);
	const FBox2D B = Grid.Bounds();
	TestTrue(TEXT("bounds valid"), B.bIsValid);
	for (const FHex& Hex : Grid.Tiles())
	{
		for (const FVector2D& C : Grid.Corners(Hex))
		{
			TestTrue(TEXT("corner within bounds"), B.ExpandBy(0.01).IsInside(C));
		}
	}
	// The map is symmetric about the origin.
	TestEqual(TEXT("symmetric X"), B.Min.X, -B.Max.X, 0.01);
	TestEqual(TEXT("symmetric Y"), B.Min.Y, -B.Max.Y, 0.01);
	return true;
}

#endif
```

- [ ] **Step 2: Add a header stub so the tests compile, then run them and expect FAIL**

`Source/MuraBito/Public/HexGrid.h`:

```cpp
#pragma once

#include "CoreMinimal.h"

/** Axial hex coordinate. The third cube coordinate is S = -Q - R. */
struct MURABITO_API FHex
{
	int32 Q = 0;
	int32 R = 0;

	FHex() = default;
	FHex(int32 InQ, int32 InR) : Q(InQ), R(InR) {}

	int32 S() const { return -Q - R; }

	bool operator==(const FHex& Other) const { return Q == Other.Q && R == Other.R; }
	bool operator!=(const FHex& Other) const { return !(*this == Other); }
	FHex operator+(const FHex& Other) const { return FHex(Q + Other.Q, R + Other.R); }

	friend uint32 GetTypeHash(const FHex& Hex) { return HashCombine(::GetTypeHash(Hex.Q), ::GetTypeHash(Hex.R)); }
};

/**
 * Pointy-top hex grid on the flat XY plane: a hexagon-shaped map of radius Radius around tile (0,0).
 * TileSize is center-to-corner in cm, which is also the side length. Knows nothing about terrain.
 */
struct MURABITO_API FHexGrid
{
	float TileSize = 300.f;
	int32 Radius = 12;

	FHexGrid() = default;
	FHexGrid(float InTileSize, int32 InRadius) : TileSize(InTileSize), Radius(InRadius) {}

	FVector2D HexToXY(const FHex& Hex) const;
	FHex XYToHex(const FVector2D& XY) const;

	/** Corner i is at angle 60*i - 30 degrees; edge i runs from corner i to corner (i+1)%6. */
	TStaticArray<FVector2D, 6> Corners(const FHex& Hex) const;

	static TStaticArray<FHex, 6> Neighbors(const FHex& Hex);
	static int32 Distance(const FHex& A, const FHex& B);

	bool Contains(const FHex& Hex) const;
	TArray<FHex> Tiles() const;
	int32 NumTiles() const;

	/** XY box around every corner of every tile. */
	FBox2D Bounds() const;
};
```

`Source/MuraBito/Private/HexGrid.cpp` (stub, so the tests link and fail):

```cpp
#include "HexGrid.h"

FVector2D FHexGrid::HexToXY(const FHex& Hex) const { return FVector2D::ZeroVector; }
FHex FHexGrid::XYToHex(const FVector2D& XY) const { return FHex(); }
TStaticArray<FVector2D, 6> FHexGrid::Corners(const FHex& Hex) const { return TStaticArray<FVector2D, 6>(InPlace, FVector2D::ZeroVector); }
TStaticArray<FHex, 6> FHexGrid::Neighbors(const FHex& Hex) { return TStaticArray<FHex, 6>(InPlace, FHex()); }
int32 FHexGrid::Distance(const FHex& A, const FHex& B) { return 0; }
bool FHexGrid::Contains(const FHex& Hex) const { return false; }
TArray<FHex> FHexGrid::Tiles() const { return {}; }
int32 FHexGrid::NumTiles() const { return 0; }
FBox2D FHexGrid::Bounds() const { return FBox2D(ForceInit); }
```

Delete `Source/MuraBito/Private/Tests/SmokeTest.cpp`.

Run: `$EXP/scripts/test.sh MuraBito.HexGrid`
Expected: it builds, then FAILS with several `Result={Fail}` lines.

- [ ] **Step 3: Implement**

Replace `Source/MuraBito/Private/HexGrid.cpp` with:

```cpp
#include "HexGrid.h"

namespace
{
	const double Sqrt3 = FMath::Sqrt(3.0);

	const FHex Directions[6] = {
		FHex(1, 0), FHex(1, -1), FHex(0, -1), FHex(-1, 0), FHex(-1, 1), FHex(0, 1),
	};
}

FVector2D FHexGrid::HexToXY(const FHex& Hex) const
{
	return FVector2D(
		TileSize * Sqrt3 * (Hex.Q + Hex.R / 2.0),
		TileSize * 1.5 * Hex.R);
}

FHex FHexGrid::XYToHex(const FVector2D& XY) const
{
	const double FQ = (Sqrt3 / 3.0 * XY.X - 1.0 / 3.0 * XY.Y) / TileSize;
	const double FR = (2.0 / 3.0 * XY.Y) / TileSize;
	const double FS = -FQ - FR;

	// Cube rounding: round all three, then fix the one with the largest rounding error.
	double RQ = FMath::RoundHalfFromZero(FQ);
	double RR = FMath::RoundHalfFromZero(FR);
	const double RS = FMath::RoundHalfFromZero(FS);

	const double DQ = FMath::Abs(RQ - FQ);
	const double DR = FMath::Abs(RR - FR);
	const double DS = FMath::Abs(RS - FS);

	if (DQ > DR && DQ > DS)
	{
		RQ = -RR - RS;
	}
	else if (DR > DS)
	{
		RR = -RQ - RS;
	}
	return FHex(static_cast<int32>(RQ), static_cast<int32>(RR));
}

TStaticArray<FVector2D, 6> FHexGrid::Corners(const FHex& Hex) const
{
	const FVector2D Center = HexToXY(Hex);
	TStaticArray<FVector2D, 6> Result;
	for (int32 i = 0; i < 6; ++i)
	{
		const double Angle = FMath::DegreesToRadians(60.0 * i - 30.0);
		Result[i] = Center + TileSize * FVector2D(FMath::Cos(Angle), FMath::Sin(Angle));
	}
	return Result;
}

TStaticArray<FHex, 6> FHexGrid::Neighbors(const FHex& Hex)
{
	TStaticArray<FHex, 6> Result;
	for (int32 i = 0; i < 6; ++i)
	{
		Result[i] = Hex + Directions[i];
	}
	return Result;
}

int32 FHexGrid::Distance(const FHex& A, const FHex& B)
{
	return (FMath::Abs(A.Q - B.Q) + FMath::Abs(A.R - B.R) + FMath::Abs(A.S() - B.S())) / 2;
}

bool FHexGrid::Contains(const FHex& Hex) const
{
	return Distance(Hex, FHex(0, 0)) <= Radius;
}

TArray<FHex> FHexGrid::Tiles() const
{
	TArray<FHex> Result;
	Result.Reserve(NumTiles());
	for (int32 Q = -Radius; Q <= Radius; ++Q)
	{
		const int32 RMin = FMath::Max(-Radius, -Q - Radius);
		const int32 RMax = FMath::Min(Radius, -Q + Radius);
		for (int32 R = RMin; R <= RMax; ++R)
		{
			Result.Add(FHex(Q, R));
		}
	}
	return Result;
}

int32 FHexGrid::NumTiles() const
{
	return 3 * Radius * Radius + 3 * Radius + 1;
}

FBox2D FHexGrid::Bounds() const
{
	FBox2D Box(ForceInit);
	for (const FHex& Hex : Tiles())
	{
		for (const FVector2D& Corner : Corners(Hex))
		{
			Box += Corner;
		}
	}
	return Box;
}
```

- [ ] **Step 4: Run the tests and expect PASS**

Run: `$EXP/scripts/test.sh MuraBito.HexGrid`
Expected: 7 tests `Result={Success}`, `TESTS PASSED`.

- [ ] **Step 5: Commit**

```bash
W=/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04
git -C $W rev-parse --abbrev-ref HEAD   # must print worktree-exp-04
git -C $W add -A Experiments/exp-04/Source
git -C $W commit -m "exp-04: FHexGrid pointy-top axial hex math with tests

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `FTerrainHeight`: seeded height function

**Files:**
- Create: `$EXP/Source/MuraBito/Public/TerrainHeight.h`, `$EXP/Source/MuraBito/Private/TerrainHeight.cpp`
- Test: `$EXP/Source/MuraBito/Private/Tests/TerrainHeightTests.cpp`

**Interfaces:**
- Produces: `struct FTerrainHeight { FTerrainHeight(); explicit FTerrainHeight(int32 InSeed, float InAmplitude = 600.f, float InWavelength = 4000.f, int32 InOctaves = 4); float Height(double X, double Y) const; FVector Normal(double X, double Y) const; int32 GetSeed() const; float GetAmplitude() const; }`. The guarantee is `|Height| <= Amplitude`, in cm.

- [ ] **Step 1: Write the failing tests**

`Source/MuraBito/Private/Tests/TerrainHeightTests.cpp`:

```cpp
#include "Misc/AutomationTest.h"
#include "TerrainHeight.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	constexpr EAutomationTestFlags TerrainTestFlags =
		EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter;

	TArray<FVector2D> SamplePoints()
	{
		TArray<FVector2D> Points;
		for (int32 i = -5; i <= 5; ++i)
		{
			for (int32 j = -5; j <= 5; ++j)
			{
				Points.Add(FVector2D(i * 1234.5, j * 987.6));
			}
		}
		return Points;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTerrainHeightDeterministicTest, "MuraBito.TerrainHeight.Deterministic", TerrainTestFlags)
bool FTerrainHeightDeterministicTest::RunTest(const FString& Parameters)
{
	const FTerrainHeight A(42);
	const FTerrainHeight B(42);
	for (const FVector2D& P : SamplePoints())
	{
		TestEqual(TEXT("same seed, same height"), A.Height(P.X, P.Y), B.Height(P.X, P.Y));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTerrainHeightSeedsDifferTest, "MuraBito.TerrainHeight.SeedsDiffer", TerrainTestFlags)
bool FTerrainHeightSeedsDifferTest::RunTest(const FString& Parameters)
{
	const FTerrainHeight A(1);
	const FTerrainHeight B(2);
	int32 Different = 0;
	for (const FVector2D& P : SamplePoints())
	{
		if (FMath::Abs(A.Height(P.X, P.Y) - B.Height(P.X, P.Y)) > 1.f)
		{
			++Different;
		}
	}
	TestTrue(TEXT("most sample points differ between seeds"), Different > SamplePoints().Num() / 2);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTerrainHeightRangeTest, "MuraBito.TerrainHeight.Range", TerrainTestFlags)
bool FTerrainHeightRangeTest::RunTest(const FString& Parameters)
{
	const FTerrainHeight H(7, 600.f);
	float Min = TNumericLimits<float>::Max();
	float Max = TNumericLimits<float>::Lowest();
	for (int32 i = -60; i <= 60; ++i)
	{
		for (int32 j = -60; j <= 60; ++j)
		{
			const float Z = H.Height(i * 113.0, j * 113.0);
			Min = FMath::Min(Min, Z);
			Max = FMath::Max(Max, Z);
		}
	}
	TestTrue(TEXT("never above amplitude"), Max <= 600.f);
	TestTrue(TEXT("never below -amplitude"), Min >= -600.f);
	// It's hilly, not flat: the spread over about 136 m is a real fraction of the amplitude.
	TestTrue(TEXT("has relief"), Max - Min > 200.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTerrainHeightNormalTest, "MuraBito.TerrainHeight.Normal", TerrainTestFlags)
bool FTerrainHeightNormalTest::RunTest(const FString& Parameters)
{
	const FTerrainHeight H(3);
	for (const FVector2D& P : SamplePoints())
	{
		const FVector N = H.Normal(P.X, P.Y);
		TestTrue(TEXT("unit length"), FMath::IsNearlyEqual(N.Size(), 1.0, 1e-4));
		TestTrue(TEXT("points up"), N.Z > 0.0);
	}
	// A flat height function has a straight-up normal.
	const FTerrainHeight Flat(3, 0.f);
	TestTrue(TEXT("flat normal"), Flat.Normal(100.0, 200.0).Equals(FVector::UpVector, 1e-4));
	return true;
}

#endif
```

- [ ] **Step 2: Add a header plus stub, run, and expect FAIL**

`Source/MuraBito/Public/TerrainHeight.h`:

```cpp
#pragma once

#include "CoreMinimal.h"

/**
 * Seeded, deterministic terrain height: layered Perlin noise over XY, in cm.
 * The terrain mesh and the hex overlay both sample this, so the draped grid matches the surface exactly.
 */
struct MURABITO_API FTerrainHeight
{
	FTerrainHeight() : FTerrainHeight(0) {}
	explicit FTerrainHeight(int32 InSeed, float InAmplitude = 600.f, float InWavelength = 4000.f, int32 InOctaves = 4);

	/** Height at (X, Y). Always within [-Amplitude, Amplitude]. */
	float Height(double X, double Y) const;

	/** Unit surface normal at (X, Y), from central differences. */
	FVector Normal(double X, double Y) const;

	int32 GetSeed() const { return Seed; }
	float GetAmplitude() const { return Amplitude; }

private:
	int32 Seed;
	float Amplitude;
	float Wavelength;
	/** One random offset per octave, from Seed. Its length is the octave count. */
	TArray<FVector2D> OctaveOffsets;
};
```

`Source/MuraBito/Private/TerrainHeight.cpp` (stub):

```cpp
#include "TerrainHeight.h"

FTerrainHeight::FTerrainHeight(int32 InSeed, float InAmplitude, float InWavelength, int32 InOctaves)
	: Seed(InSeed), Amplitude(InAmplitude), Wavelength(InWavelength) {}

float FTerrainHeight::Height(double X, double Y) const { return 0.f; }
FVector FTerrainHeight::Normal(double X, double Y) const { return FVector::ZeroVector; }
```

Run: `$EXP/scripts/test.sh MuraBito.TerrainHeight`
Expected: FAIL (`SeedsDiffer`, `Range` relief, and `Normal` fail).

- [ ] **Step 3: Implement**

Replace `Source/MuraBito/Private/TerrainHeight.cpp` with:

```cpp
#include "TerrainHeight.h"

FTerrainHeight::FTerrainHeight(int32 InSeed, float InAmplitude, float InWavelength, int32 InOctaves)
	: Seed(InSeed), Amplitude(InAmplitude), Wavelength(InWavelength)
{
	FRandomStream Stream(InSeed);
	for (int32 i = 0; i < FMath::Max(1, InOctaves); ++i)
	{
		OctaveOffsets.Add(FVector2D(Stream.FRandRange(-1000.f, 1000.f), Stream.FRandRange(-1000.f, 1000.f)));
	}
}

float FTerrainHeight::Height(double X, double Y) const
{
	double Sum = 0.0;
	double Norm = 0.0;
	double Frequency = 1.0 / Wavelength;
	double Weight = 1.0;
	for (const FVector2D& Offset : OctaveOffsets)
	{
		const FVector2D P = FVector2D(X, Y) * Frequency + Offset;
		Sum += Weight * FMath::PerlinNoise2D(P);
		Norm += Weight;
		Frequency *= 2.0;
		Weight *= 0.5;
	}
	const double Z = Amplitude * (Sum / Norm);
	return static_cast<float>(FMath::Clamp(Z, -static_cast<double>(Amplitude), static_cast<double>(Amplitude)));
}

FVector FTerrainHeight::Normal(double X, double Y) const
{
	constexpr double Eps = 10.0;
	const double DZDX = (Height(X + Eps, Y) - Height(X - Eps, Y)) / (2.0 * Eps);
	const double DZDY = (Height(X, Y + Eps) - Height(X, Y - Eps)) / (2.0 * Eps);
	return FVector(-DZDX, -DZDY, 1.0).GetSafeNormal();
}
```

- [ ] **Step 4: Run the tests and expect PASS**

Run: `$EXP/scripts/test.sh MuraBito.TerrainHeight`
Expected: 4 `Result={Success}`, `TESTS PASSED`.

If `has relief` fails because Perlin output is small, don't change the test. Raise the default amplitude until it passes, or rescale the noise sum (for example by `1.4` before the clamp). Say which you did in the commit message.

- [ ] **Step 5: Commit**

```bash
W=/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04
git -C $W rev-parse --abbrev-ref HEAD   # must print worktree-exp-04
git -C $W add -A Experiments/exp-04/Source
git -C $W commit -m "exp-04: FTerrainHeight seeded layered-noise height function with tests

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `MeshBuilders`: terrain mesh and draped hex ribbons

**Files:**
- Create: `$EXP/Source/MuraBito/Public/MeshData.h`, `$EXP/Source/MuraBito/Public/MeshBuilders.h`, `$EXP/Source/MuraBito/Private/MeshBuilders.cpp`
- Test: `$EXP/Source/MuraBito/Private/Tests/MeshBuildersTests.cpp`

**Interfaces:**
- Consumes: `FHexGrid` (Task 2), `FTerrainHeight` (Task 3).
- Produces:
  - `struct FMeshData { TArray<FVector> Vertices; TArray<int32> Triangles; TArray<FVector> Normals; TArray<FVector2D> UVs; TArray<FLinearColor> Colors; }`
  - `struct FDrapeParams { float Width = 8.f; float Lift = 10.f; float SegmentLength = 25.f; }`
  - `namespace MeshBuilders { FMeshData BuildTerrain(const FTerrainHeight&, const FBox2D& Area, float Spacing); FMeshData BuildHexEdges(const FHexGrid&, const FTerrainHeight&, const FDrapeParams&, const FLinearColor&); FMeshData BuildHexOutline(const FHexGrid&, const FHex&, const FTerrainHeight&, const FDrapeParams&, const FLinearColor&); int32 SegmentsPerEdge(float EdgeLength, const FDrapeParams&); }`
  - Every triangle faces up: `CrossProduct(B - A, C - A).Z < 0`. Each ribbon edge has `SegmentsPerEdge + 1` vertex pairs.

- [ ] **Step 1: Write the failing tests**

`Source/MuraBito/Private/Tests/MeshBuildersTests.cpp`:

```cpp
#include "Misc/AutomationTest.h"
#include "MeshBuilders.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	constexpr EAutomationTestFlags MeshTestFlags =
		EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter;

	/** UE front faces: CrossProduct(B - A, C - A) points away from the viewer, so up-facing means Z < 0. */
	int32 CountNonUpFacing(const FMeshData& Mesh)
	{
		int32 Bad = 0;
		for (int32 i = 0; i + 2 < Mesh.Triangles.Num(); i += 3)
		{
			const FVector& A = Mesh.Vertices[Mesh.Triangles[i]];
			const FVector& B = Mesh.Vertices[Mesh.Triangles[i + 1]];
			const FVector& C = Mesh.Vertices[Mesh.Triangles[i + 2]];
			if (FVector::CrossProduct(B - A, C - A).Z >= 0.0)
			{
				++Bad;
			}
		}
		return Bad;
	}

	bool ArraysConsistent(const FMeshData& Mesh)
	{
		const int32 N = Mesh.Vertices.Num();
		return Mesh.Normals.Num() == N && Mesh.UVs.Num() == N && Mesh.Colors.Num() == N
			&& Mesh.Triangles.Num() % 3 == 0
			&& !Mesh.Triangles.ContainsByPredicate([N](int32 I) { return I < 0 || I >= N; });
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FTerrainMeshTest, "MuraBito.MeshBuilders.Terrain", MeshTestFlags)
bool FTerrainMeshTest::RunTest(const FString& Parameters)
{
	const FTerrainHeight Height(5);
	const FBox2D Area(FVector2D(-1000, -500), FVector2D(1000, 500));
	const FMeshData Mesh = MeshBuilders::BuildTerrain(Height, Area, 100.f);

	// 2000 x 1000 at 100 cm spacing -> 21 x 11 vertices, 20 x 10 quads.
	TestEqual(TEXT("vertex count"), Mesh.Vertices.Num(), 21 * 11);
	TestEqual(TEXT("triangle index count"), Mesh.Triangles.Num(), 20 * 10 * 6);
	TestTrue(TEXT("arrays consistent"), ArraysConsistent(Mesh));
	TestEqual(TEXT("all triangles face up"), CountNonUpFacing(Mesh), 0);

	FBox2D Covered(ForceInit);
	for (const FVector& V : Mesh.Vertices)
	{
		Covered += FVector2D(V);
		TestEqual(TEXT("vertex on height function"), V.Z, static_cast<double>(Height.Height(V.X, V.Y)), 0.01);
	}
	TestTrue(TEXT("covers area min"), Covered.Min.Equals(Area.Min, 0.01));
	TestTrue(TEXT("covers area max"), Covered.Max.Equals(Area.Max, 0.01));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FHexEdgesTest, "MuraBito.MeshBuilders.HexEdges", MeshTestFlags)
bool FHexEdgesTest::RunTest(const FString& Parameters)
{
	const FHexGrid Grid(300.f, 2);
	const FTerrainHeight Height(9);
	const FDrapeParams Params;
	const FMeshData Mesh = MeshBuilders::BuildHexEdges(Grid, Height, Params, FLinearColor::Black);

	TestTrue(TEXT("arrays consistent"), ArraysConsistent(Mesh));
	TestEqual(TEXT("all triangles face up"), CountNonUpFacing(Mesh), 0);

	// A hexagon-shaped map of radius R with T tiles has 3T + 6R + 3 unique edges.
	const int32 T = Grid.NumTiles();
	const int32 ExpectedEdges = 3 * T + 6 * 2 + 3;
	const int32 Segments = MeshBuilders::SegmentsPerEdge(Grid.TileSize, Params);
	TestEqual(TEXT("segments per 300cm edge at 25cm"), Segments, 12);
	TestEqual(TEXT("vertices = edges * (segments + 1) * 2"), Mesh.Vertices.Num(), ExpectedEdges * (Segments + 1) * 2);
	TestEqual(TEXT("triangles = edges * segments * 2"), Mesh.Triangles.Num() / 3, ExpectedEdges * Segments * 2);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FHexDrapeTest, "MuraBito.MeshBuilders.Drape", MeshTestFlags)
bool FHexDrapeTest::RunTest(const FString& Parameters)
{
	const FHexGrid Grid(300.f, 3);
	const FTerrainHeight Height(11);
	FDrapeParams Params;
	Params.Lift = 12.f;
	const FMeshData Mesh = MeshBuilders::BuildHexEdges(Grid, Height, Params, FLinearColor::Black);
	for (const FVector& V : Mesh.Vertices)
	{
		TestEqual(TEXT("vertex Z = Height + Lift"), V.Z, static_cast<double>(Height.Height(V.X, V.Y) + Params.Lift), 0.01);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FHexOutlineTest, "MuraBito.MeshBuilders.Outline", MeshTestFlags)
bool FHexOutlineTest::RunTest(const FString& Parameters)
{
	const FHexGrid Grid(300.f, 12);
	const FTerrainHeight Height(4);
	FDrapeParams Params;
	Params.Width = 20.f;
	const FHex Hex(3, -1);
	const FMeshData Mesh = MeshBuilders::BuildHexOutline(Grid, Hex, Height, Params, FLinearColor::Yellow);

	const int32 Segments = MeshBuilders::SegmentsPerEdge(Grid.TileSize, Params);
	TestTrue(TEXT("arrays consistent"), ArraysConsistent(Mesh));
	TestEqual(TEXT("six edges"), Mesh.Vertices.Num(), 6 * (Segments + 1) * 2);
	TestEqual(TEXT("all triangles face up"), CountNonUpFacing(Mesh), 0);

	// Every vertex lies within half a width of the tile's outline, and all are the given color.
	const FVector2D Center = Grid.HexToXY(Hex);
	for (int32 i = 0; i < Mesh.Vertices.Num(); ++i)
	{
		const double R = FVector2D::Distance(FVector2D(Mesh.Vertices[i]), Center);
		// The outline runs between the inradius (sqrt3/2 * size) and the circumradius (size).
		TestTrue(TEXT("near outline"), R >= Grid.TileSize * FMath::Sqrt(3.0) / 2.0 - Params.Width && R <= Grid.TileSize + Params.Width);
		TestTrue(TEXT("color"), Mesh.Colors[i].Equals(FLinearColor::Yellow));
	}
	return true;
}

#endif
```

- [ ] **Step 2: Add headers plus stub, run, and expect FAIL**

`Source/MuraBito/Public/MeshData.h`:

```cpp
#pragma once

#include "CoreMinimal.h"

/** Plain mesh arrays, in the layout UProceduralMeshComponent::CreateMeshSection_LinearColor takes. */
struct FMeshData
{
	TArray<FVector> Vertices;
	TArray<int32> Triangles;
	TArray<FVector> Normals;
	TArray<FVector2D> UVs;
	TArray<FLinearColor> Colors;
};
```

`Source/MuraBito/Public/MeshBuilders.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "HexGrid.h"
#include "MeshData.h"
#include "TerrainHeight.h"

/** How a line on the flat grid is draped onto the terrain as a thin ribbon. */
struct FDrapeParams
{
	float Width = 8.f;          // cm, ribbon width
	float Lift = 10.f;          // cm above the height function, so lines don't sink into the terrain
	float SegmentLength = 25.f; // cm, the longest straight piece along an edge
};

/**
 * Builds mesh arrays from pure data. Every triangle faces up (+Z):
 * CrossProduct(B - A, C - A).Z < 0, the engine's front-face convention.
 */
namespace MeshBuilders
{
	/** Regular grid over Area at Spacing, with Z from Height and vertex colors graded by height. */
	MURABITO_API FMeshData BuildTerrain(const FTerrainHeight& Height, const FBox2D& Area, float Spacing);

	/** Every unique edge of every tile in Grid, as draped ribbons. */
	MURABITO_API FMeshData BuildHexEdges(const FHexGrid& Grid, const FTerrainHeight& Height, const FDrapeParams& Params, const FLinearColor& Color);

	/** The six edges of one tile, as draped ribbons. */
	MURABITO_API FMeshData BuildHexOutline(const FHexGrid& Grid, const FHex& Hex, const FTerrainHeight& Height, const FDrapeParams& Params, const FLinearColor& Color);

	/** Straight pieces per edge of EdgeLength: ceil(EdgeLength / SegmentLength), at least 1. */
	MURABITO_API int32 SegmentsPerEdge(float EdgeLength, const FDrapeParams& Params);
}
```

`Source/MuraBito/Private/MeshBuilders.cpp` (stub):

```cpp
#include "MeshBuilders.h"

namespace MeshBuilders
{
	FMeshData BuildTerrain(const FTerrainHeight& Height, const FBox2D& Area, float Spacing) { return {}; }
	FMeshData BuildHexEdges(const FHexGrid& Grid, const FTerrainHeight& Height, const FDrapeParams& Params, const FLinearColor& Color) { return {}; }
	FMeshData BuildHexOutline(const FHexGrid& Grid, const FHex& Hex, const FTerrainHeight& Height, const FDrapeParams& Params, const FLinearColor& Color) { return {}; }
	int32 SegmentsPerEdge(float EdgeLength, const FDrapeParams& Params) { return 0; }
}
```

Run: `$EXP/scripts/test.sh MuraBito.MeshBuilders`
Expected: FAIL.

- [ ] **Step 3: Implement**

Replace `Source/MuraBito/Private/MeshBuilders.cpp` with:

```cpp
#include "MeshBuilders.h"

namespace
{
	const FLinearColor LowColor(0.18f, 0.32f, 0.10f);  // grass
	const FLinearColor HighColor(0.42f, 0.38f, 0.31f); // rocky grey-brown

	/** Appends triangle (A, B, C), swapping B and C if needed so it faces up. */
	void AddUpTriangle(FMeshData& Mesh, int32 A, int32 B, int32 C)
	{
		const FVector& VA = Mesh.Vertices[A];
		if (FVector::CrossProduct(Mesh.Vertices[B] - VA, Mesh.Vertices[C] - VA).Z > 0.0)
		{
			Swap(B, C);
		}
		Mesh.Triangles.Append({ A, B, C });
	}

	/** Draped ribbon from A to B on the flat plane: pairs of vertices on either side of the line, lifted onto the terrain. */
	void AddRibbon(FMeshData& Mesh, const FVector2D& A, const FVector2D& B, const FTerrainHeight& Height,
		const FDrapeParams& Params, const FLinearColor& Color)
	{
		const FVector2D Dir = (B - A).GetSafeNormal();
		const FVector2D Side = FVector2D(-Dir.Y, Dir.X) * (Params.Width * 0.5);
		const int32 Segments = MeshBuilders::SegmentsPerEdge(FVector2D::Distance(A, B), Params);
		const int32 First = Mesh.Vertices.Num();

		for (int32 i = 0; i <= Segments; ++i)
		{
			const double T = static_cast<double>(i) / Segments;
			const FVector2D P = FMath::Lerp(A, B, T);
			for (int32 SideIdx = 0; SideIdx < 2; ++SideIdx)
			{
				const FVector2D Q = SideIdx == 0 ? P - Side : P + Side;
				Mesh.Vertices.Add(FVector(Q.X, Q.Y, Height.Height(Q.X, Q.Y) + Params.Lift));
				Mesh.Normals.Add(Height.Normal(Q.X, Q.Y));
				Mesh.UVs.Add(FVector2D(T, SideIdx));
				Mesh.Colors.Add(Color);
			}
		}
		for (int32 i = 0; i < Segments; ++i)
		{
			const int32 L0 = First + 2 * i;
			const int32 R0 = L0 + 1;
			const int32 L1 = L0 + 2;
			const int32 R1 = L0 + 3;
			AddUpTriangle(Mesh, L0, R0, L1);
			AddUpTriangle(Mesh, R0, R1, L1);
		}
	}

	/** Integer-cm key for a corner, so shared edges between neighboring tiles dedupe exactly. */
	FIntPoint CornerKey(const FVector2D& P)
	{
		return FIntPoint(FMath::RoundToInt(P.X), FMath::RoundToInt(P.Y));
	}

	bool KeyLess(const FIntPoint& A, const FIntPoint& B)
	{
		return A.X < B.X || (A.X == B.X && A.Y < B.Y);
	}
}

namespace MeshBuilders
{
	FMeshData BuildTerrain(const FTerrainHeight& Height, const FBox2D& Area, float Spacing)
	{
		FMeshData Mesh;
		const FVector2D Size = Area.GetSize();
		const int32 NumX = FMath::Max(2, FMath::RoundToInt(Size.X / Spacing) + 1);
		const int32 NumY = FMath::Max(2, FMath::RoundToInt(Size.Y / Spacing) + 1);
		const float Amplitude = FMath::Max(Height.GetAmplitude(), 1.f);

		for (int32 IY = 0; IY < NumY; ++IY)
		{
			for (int32 IX = 0; IX < NumX; ++IX)
			{
				const double U = static_cast<double>(IX) / (NumX - 1);
				const double V = static_cast<double>(IY) / (NumY - 1);
				const double X = FMath::Lerp(Area.Min.X, Area.Max.X, U);
				const double Y = FMath::Lerp(Area.Min.Y, Area.Max.Y, V);
				const float Z = Height.Height(X, Y);
				Mesh.Vertices.Add(FVector(X, Y, Z));
				Mesh.Normals.Add(Height.Normal(X, Y));
				Mesh.UVs.Add(FVector2D(U, V));
				const float T = FMath::Clamp((Z + Amplitude) / (2.f * Amplitude), 0.f, 1.f);
				Mesh.Colors.Add(FMath::Lerp(LowColor, HighColor, FMath::SmoothStep(0.35f, 0.85f, T)));
			}
		}
		for (int32 IY = 0; IY < NumY - 1; ++IY)
		{
			for (int32 IX = 0; IX < NumX - 1; ++IX)
			{
				const int32 I = IX + IY * NumX;
				AddUpTriangle(Mesh, I, I + NumX, I + 1);
				AddUpTriangle(Mesh, I + 1, I + NumX, I + NumX + 1);
			}
		}
		return Mesh;
	}

	FMeshData BuildHexEdges(const FHexGrid& Grid, const FTerrainHeight& Height, const FDrapeParams& Params, const FLinearColor& Color)
	{
		FMeshData Mesh;
		TSet<TPair<FIntPoint, FIntPoint>> Seen;
		for (const FHex& Hex : Grid.Tiles())
		{
			const TStaticArray<FVector2D, 6> C = Grid.Corners(Hex);
			for (int32 i = 0; i < 6; ++i)
			{
				const FVector2D& A = C[i];
				const FVector2D& B = C[(i + 1) % 6];
				FIntPoint KA = CornerKey(A);
				FIntPoint KB = CornerKey(B);
				if (KeyLess(KB, KA))
				{
					Swap(KA, KB);
				}
				bool bAlreadySeen = false;
				Seen.Add(TPair<FIntPoint, FIntPoint>(KA, KB), &bAlreadySeen);
				if (!bAlreadySeen)
				{
					AddRibbon(Mesh, A, B, Height, Params, Color);
				}
			}
		}
		return Mesh;
	}

	FMeshData BuildHexOutline(const FHexGrid& Grid, const FHex& Hex, const FTerrainHeight& Height, const FDrapeParams& Params, const FLinearColor& Color)
	{
		FMeshData Mesh;
		const TStaticArray<FVector2D, 6> C = Grid.Corners(Hex);
		for (int32 i = 0; i < 6; ++i)
		{
			AddRibbon(Mesh, C[i], C[(i + 1) % 6], Height, Params, Color);
		}
		return Mesh;
	}

	int32 SegmentsPerEdge(float EdgeLength, const FDrapeParams& Params)
	{
		// The small epsilon keeps 300 / 25 at 12, not 13, after float error.
		return FMath::Max(1, FMath::CeilToInt(EdgeLength / Params.SegmentLength - 1e-3f));
	}
}
```


- [ ] **Step 4: Run the tests and expect PASS**

Run: `$EXP/scripts/test.sh MuraBito.MeshBuilders`
Expected: 4 `Result={Success}`, `TESTS PASSED`.

Then run: `$EXP/scripts/test.sh`
Expected: all `MuraBito.*` tests pass.

- [ ] **Step 5: Commit**

```bash
W=/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04
git -C $W rev-parse --abbrev-ref HEAD   # must print worktree-exp-04
git -C $W add -A Experiments/exp-04/Source
git -C $W commit -m "exp-04: terrain mesh and draped hex ribbon builders with tests

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `CameraMath`: zoom, tilt, clamp and pan mapping

**Files:**
- Create: `$EXP/Source/MuraBito/Public/CameraMath.h`, `$EXP/Source/MuraBito/Private/CameraMath.cpp`
- Test: `$EXP/Source/MuraBito/Private/Tests/CameraMathTests.cpp`

**Interfaces:**
- Produces:
  - `struct FZoomRange { float NearArm = 1500.f; float FarArm = 12000.f; float NearPitch = -45.f; float FarPitch = -75.f; }`. Pitch is in UE degrees, where negative looks down.
  - `namespace CameraMath { float ArmLength(const FZoomRange&, float Zoom01); float Pitch(const FZoomRange&, float Zoom01); FVector2D ClampToBounds(const FVector2D&, const FBox2D&); FVector2D ScreenDirToWorld(const FVector2D& ScreenDir); FVector2D DragToWorld(const FVector2D& PixelDelta, float CmPerPixel); float PanSpeed(float BaseSpeed, const FZoomRange&, float Zoom01); }`
  - `Zoom01` runs from 0 (near) to 1 (far). ScreenDir is (X = right, Y = up the screen), and world is (X = forward, Y = right), for a camera at yaw 0.

- [ ] **Step 1: Write the failing tests**

`Source/MuraBito/Private/Tests/CameraMathTests.cpp`:

```cpp
#include "Misc/AutomationTest.h"
#include "CameraMath.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	constexpr EAutomationTestFlags CameraTestFlags =
		EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCameraZoomTiltTest, "MuraBito.CameraMath.ZoomTilt", CameraTestFlags)
bool FCameraZoomTiltTest::RunTest(const FString& Parameters)
{
	const FZoomRange Z;
	TestEqual(TEXT("near arm"), CameraMath::ArmLength(Z, 0.f), 1500.f, 0.01f);
	TestEqual(TEXT("far arm"), CameraMath::ArmLength(Z, 1.f), 12000.f, 0.01f);
	TestEqual(TEXT("mid arm"), CameraMath::ArmLength(Z, 0.5f), 6750.f, 0.01f);
	TestEqual(TEXT("near pitch is oblique"), CameraMath::Pitch(Z, 0.f), -45.f, 0.01f);
	TestEqual(TEXT("far pitch is steep"), CameraMath::Pitch(Z, 1.f), -75.f, 0.01f);
	TestEqual(TEXT("mid pitch"), CameraMath::Pitch(Z, 0.5f), -60.f, 0.01f);
	TestEqual(TEXT("zoom clamps low"), CameraMath::ArmLength(Z, -1.f), 1500.f, 0.01f);
	TestEqual(TEXT("zoom clamps high"), CameraMath::Pitch(Z, 2.f), -75.f, 0.01f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCameraClampTest, "MuraBito.CameraMath.Clamp", CameraTestFlags)
bool FCameraClampTest::RunTest(const FString& Parameters)
{
	const FBox2D B(FVector2D(-100, -50), FVector2D(100, 50));
	TestTrue(TEXT("inside unchanged"), CameraMath::ClampToBounds(FVector2D(10, 20), B).Equals(FVector2D(10, 20)));
	TestTrue(TEXT("clamped max"), CameraMath::ClampToBounds(FVector2D(500, 500), B).Equals(FVector2D(100, 50)));
	TestTrue(TEXT("clamped min"), CameraMath::ClampToBounds(FVector2D(-500, -500), B).Equals(FVector2D(-100, -50)));
	TestTrue(TEXT("clamped one axis"), CameraMath::ClampToBounds(FVector2D(0, 99), B).Equals(FVector2D(0, 50)));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCameraPanMappingTest, "MuraBito.CameraMath.PanMapping", CameraTestFlags)
bool FCameraPanMappingTest::RunTest(const FString& Parameters)
{
	// Screen up -> world forward (+X); screen right -> world right (+Y).
	TestTrue(TEXT("up is forward"), CameraMath::ScreenDirToWorld(FVector2D(0, 1)).Equals(FVector2D(1, 0)));
	TestTrue(TEXT("right is right"), CameraMath::ScreenDirToWorld(FVector2D(1, 0)).Equals(FVector2D(0, 1)));

	// Dragging moves the ground with the cursor: the mouse moves right (+px X), so the camera moves left (-Y);
	// the mouse moves down (+px Y, screen coords), so the camera moves forward (+X).
	TestTrue(TEXT("drag right"), CameraMath::DragToWorld(FVector2D(10, 0), 2.f).Equals(FVector2D(0, -20)));
	TestTrue(TEXT("drag down"), CameraMath::DragToWorld(FVector2D(0, 10), 2.f).Equals(FVector2D(20, 0)));

	// Pan speed scales with arm length: twice as fast at twice the distance.
	const FZoomRange Z;
	TestEqual(TEXT("near speed is base"), CameraMath::PanSpeed(1000.f, Z, 0.f), 1000.f, 0.01f);
	TestEqual(TEXT("far speed scales"), CameraMath::PanSpeed(1000.f, Z, 1.f), 8000.f, 0.01f);
	return true;
}

#endif
```

- [ ] **Step 2: Add a header plus stub, run, and expect FAIL**

`Source/MuraBito/Public/CameraMath.h`:

```cpp
#pragma once

#include "CoreMinimal.h"

/** Zoom limits. Zoom01 = 0 is the near limit, 1 the far. Pitch is in degrees; negative looks down. */
struct FZoomRange
{
	float NearArm = 1500.f;
	float FarArm = 12000.f;
	float NearPitch = -45.f;
	float FarPitch = -75.f;
};

/** Pure helpers for the overhead camera, kept apart from the actor so they can be tested. */
namespace CameraMath
{
	MURABITO_API float ArmLength(const FZoomRange& Range, float Zoom01);

	/** Tilt follows zoom: oblique when close, steep when far. */
	MURABITO_API float Pitch(const FZoomRange& Range, float Zoom01);

	MURABITO_API FVector2D ClampToBounds(const FVector2D& Point, const FBox2D& Bounds);

	/** (right, up-screen) -> world (X forward, Y right), for a camera at yaw 0. */
	MURABITO_API FVector2D ScreenDirToWorld(const FVector2D& ScreenDir);

	/** Mouse drag in pixels (screen coords, +Y down) -> world camera offset that keeps the ground under the cursor. */
	MURABITO_API FVector2D DragToWorld(const FVector2D& PixelDelta, float CmPerPixel);

	/** Pan speed in cm/s: BaseSpeed at the near limit, scaled by arm length. */
	MURABITO_API float PanSpeed(float BaseSpeed, const FZoomRange& Range, float Zoom01);
}
```

`Source/MuraBito/Private/CameraMath.cpp` (stub):

```cpp
#include "CameraMath.h"

namespace CameraMath
{
	float ArmLength(const FZoomRange& Range, float Zoom01) { return 0.f; }
	float Pitch(const FZoomRange& Range, float Zoom01) { return 0.f; }
	FVector2D ClampToBounds(const FVector2D& Point, const FBox2D& Bounds) { return FVector2D::ZeroVector; }
	FVector2D ScreenDirToWorld(const FVector2D& ScreenDir) { return FVector2D::ZeroVector; }
	FVector2D DragToWorld(const FVector2D& PixelDelta, float CmPerPixel) { return FVector2D::ZeroVector; }
	float PanSpeed(float BaseSpeed, const FZoomRange& Range, float Zoom01) { return 0.f; }
}
```

Run: `$EXP/scripts/test.sh MuraBito.CameraMath`
Expected: FAIL.

- [ ] **Step 3: Implement**

Replace `Source/MuraBito/Private/CameraMath.cpp` with:

```cpp
#include "CameraMath.h"

namespace CameraMath
{
	float ArmLength(const FZoomRange& Range, float Zoom01)
	{
		return FMath::Lerp(Range.NearArm, Range.FarArm, FMath::Clamp(Zoom01, 0.f, 1.f));
	}

	float Pitch(const FZoomRange& Range, float Zoom01)
	{
		return FMath::Lerp(Range.NearPitch, Range.FarPitch, FMath::Clamp(Zoom01, 0.f, 1.f));
	}

	FVector2D ClampToBounds(const FVector2D& Point, const FBox2D& Bounds)
	{
		return FVector2D(
			FMath::Clamp(Point.X, Bounds.Min.X, Bounds.Max.X),
			FMath::Clamp(Point.Y, Bounds.Min.Y, Bounds.Max.Y));
	}

	FVector2D ScreenDirToWorld(const FVector2D& ScreenDir)
	{
		return FVector2D(ScreenDir.Y, ScreenDir.X);
	}

	FVector2D DragToWorld(const FVector2D& PixelDelta, float CmPerPixel)
	{
		return FVector2D(PixelDelta.Y * CmPerPixel, -PixelDelta.X * CmPerPixel);
	}

	float PanSpeed(float BaseSpeed, const FZoomRange& Range, float Zoom01)
	{
		return BaseSpeed * ArmLength(Range, Zoom01) / Range.NearArm;
	}
}
```

- [ ] **Step 4: Run the tests and expect PASS**

Run: `$EXP/scripts/test.sh MuraBito.CameraMath`
Expected: 3 `Result={Success}`, `TESTS PASSED`.

- [ ] **Step 5: Commit**

```bash
W=/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04
git -C $W rev-parse --abbrev-ref HEAD   # must print worktree-exp-04
git -C $W add -A Experiments/exp-04/Source
git -C $W commit -m "exp-04: CameraMath zoom, tilt, clamp and pan mapping with tests

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Materials, `ATerrain` and `AHexOverlay`

**Files:**
- Create: `$EXP/Source/MuraBito/Public/Materials.h`, `$EXP/Source/MuraBito/Private/Materials.cpp`
- Create: `$EXP/Source/MuraBito/Public/Terrain.h`, `$EXP/Source/MuraBito/Private/Terrain.cpp`
- Create: `$EXP/Source/MuraBito/Public/HexOverlay.h`, `$EXP/Source/MuraBito/Private/HexOverlay.cpp`

**Interfaces:**
- Consumes: `FHexGrid`, `FHex`, `FTerrainHeight`, `MeshBuilders::*`, `FDrapeParams`, `LogMuraBito`.
- Produces:
  - `namespace Materials { UMaterialInterface* LitVertexColor(); UMaterialInterface* MakeUnlitVertexColor(UObject* Outer); }`. Both return a usable material, or the engine default material with a logged warning.
  - `ATerrain : AActor { UProceduralMeshComponent* Mesh; void Build(const FTerrainHeight&, const FBox2D& Area, float Spacing); }`. It has collision, so cursor traces on `ECC_Visibility` hit it.
  - `AHexOverlay : AActor { void Build(const FHexGrid&, const FTerrainHeight&); void SetHover(TOptional<FHex>); TOptional<FHex> GetHover() const; const FHexGrid& GetGrid() const; }`. Section 0 is the grid lines and section 1 the hover outline. It has no collision.

There are no new automation tests: the logic under these actors is covered by Tasks 2–4. This task is checked by compiling and by the full suite still passing. The visual check comes in Task 7.

- [ ] **Step 1: Write `Materials`**

`Source/MuraBito/Public/Materials.h`:

```cpp
#pragma once

#include "CoreMinimal.h"

class UMaterialInterface;
class UObject;

/** Materials without project assets: engine-provided ones, or ones built in code at runtime. */
namespace Materials
{
	/** Lit material whose base color is the mesh's vertex color (/Engine/EngineDebugMaterials/VertexColorMaterial). */
	MURABITO_API UMaterialInterface* LitVertexColor();

	/**
	 * Unlit material that shows the vertex color, built in code. Needs editor-only material data, so this works
	 * when running through UnrealEditor (editor, PIE and -game). Elsewhere it falls back to LitVertexColor().
	 * The caller must keep the result referenced (e.g. in a UPROPERTY) so it isn't garbage collected.
	 */
	MURABITO_API UMaterialInterface* MakeUnlitVertexColor(UObject* Outer);
}
```

`Source/MuraBito/Private/Materials.cpp`:

```cpp
#include "Materials.h"

#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "MuraBitoLog.h"
#if WITH_EDITOR
#include "Materials/MaterialExpressionVertexColor.h"
#endif

namespace Materials
{
	UMaterialInterface* LitVertexColor()
	{
		UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial"));
		if (!Material)
		{
			UE_LOG(LogMuraBito, Warning, TEXT("VertexColorMaterial not found; using the default surface material"));
			Material = UMaterial::GetDefaultMaterial(MD_Surface);
		}
		return Material;
	}

	UMaterialInterface* MakeUnlitVertexColor(UObject* Outer)
	{
#if WITH_EDITOR
		UMaterial* Material = NewObject<UMaterial>(Outer, NAME_None, RF_Transient);
		if (UMaterialEditorOnlyData* EditorData = Material->GetEditorOnlyData())
		{
			UMaterialExpressionVertexColor* VertexColor = NewObject<UMaterialExpressionVertexColor>(Material);
			Material->GetExpressionCollection().AddExpression(VertexColor);
			EditorData->EmissiveColor.Connect(0, VertexColor);
			Material->SetShadingModel(MSM_Unlit);
			Material->PreEditChange(nullptr);
			Material->PostEditChange();
			return Material;
		}
		UE_LOG(LogMuraBito, Warning, TEXT("No editor-only material data; the overlay uses the lit vertex-color material"));
#endif
		return LitVertexColor();
	}
}
```

If any of these calls don't compile against 5.8, check the real signatures in `$UE_ROOT/Engine/Source/Runtime/Engine/Public/Materials/Material.h` and `.../MaterialExpressionIO.h`, and adapt. Keep the same behavior: vertex color into emissive, unlit.

- [ ] **Step 2: Write `ATerrain`**

`Source/MuraBito/Public/Terrain.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Terrain.generated.h"

class UProceduralMeshComponent;
struct FTerrainHeight;

/** The hilly ground: one procedural mesh built from FTerrainHeight, with collision for cursor picking. */
UCLASS()
class MURABITO_API ATerrain : public AActor
{
	GENERATED_BODY()

public:
	ATerrain();

	/** Builds (or rebuilds) the mesh over Area, sampling Height every Spacing cm. */
	void Build(const FTerrainHeight& Height, const FBox2D& Area, float Spacing);

	UPROPERTY(VisibleAnywhere, Category = "Terrain")
	TObjectPtr<UProceduralMeshComponent> Mesh;
};
```

`Source/MuraBito/Private/Terrain.cpp`:

```cpp
#include "Terrain.h"

#include "Engine/CollisionProfile.h"
#include "Materials.h"
#include "MeshBuilders.h"
#include "MuraBitoLog.h"
#include "ProceduralMeshComponent.h"

ATerrain::ATerrain()
{
	PrimaryActorTick.bCanEverTick = false;
	Mesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("Mesh"));
	Mesh->bUseAsyncCooking = true;
	Mesh->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	RootComponent = Mesh;
}

void ATerrain::Build(const FTerrainHeight& Height, const FBox2D& Area, float Spacing)
{
	const FMeshData Data = MeshBuilders::BuildTerrain(Height, Area, Spacing);
	Mesh->CreateMeshSection_LinearColor(0, Data.Vertices, Data.Triangles, Data.Normals, Data.UVs, Data.Colors,
		TArray<FProcMeshTangent>(), /*bCreateCollision=*/ true);
	Mesh->SetMaterial(0, Materials::LitVertexColor());
	UE_LOG(LogMuraBito, Log, TEXT("Terrain: %d vertices, %d triangles"), Data.Vertices.Num(), Data.Triangles.Num() / 3);
}
```

- [ ] **Step 3: Write `AHexOverlay`**

`Source/MuraBito/Public/HexOverlay.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HexGrid.h"
#include "MeshBuilders.h"
#include "TerrainHeight.h"
#include "HexOverlay.generated.h"

class UMaterialInterface;
class UProceduralMeshComponent;

/** The flat hex grid draped onto the terrain as thin lines, plus an outline on the hovered tile. */
UCLASS()
class MURABITO_API AHexOverlay : public AActor
{
	GENERATED_BODY()

public:
	AHexOverlay();

	void Build(const FHexGrid& InGrid, const FTerrainHeight& InHeight);

	/** Shows the outline on Hex, or hides it when unset. Does nothing if the tile hasn't changed. */
	void SetHover(TOptional<FHex> Hex);
	TOptional<FHex> GetHover() const { return Hover; }

	const FHexGrid& GetGrid() const { return Grid; }

	UPROPERTY(VisibleAnywhere, Category = "Hex Overlay")
	TObjectPtr<UProceduralMeshComponent> Mesh;

private:
	static constexpr int32 LinesSection = 0;
	static constexpr int32 HoverSection = 1;

	FHexGrid Grid;
	FTerrainHeight Height;
	TOptional<FHex> Hover;

	FDrapeParams LineParams;
	FDrapeParams HoverParams;
	FLinearColor LineColor = FLinearColor(0.02f, 0.02f, 0.02f);
	FLinearColor HoverColor = FLinearColor(1.0f, 0.75f, 0.1f);

	UPROPERTY()
	TObjectPtr<UMaterialInterface> Material;
};
```

`Source/MuraBito/Private/HexOverlay.cpp`:

```cpp
#include "HexOverlay.h"

#include "Materials.h"
#include "MuraBitoLog.h"
#include "ProceduralMeshComponent.h"

AHexOverlay::AHexOverlay()
{
	PrimaryActorTick.bCanEverTick = false;
	Mesh = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("Mesh"));
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetCastShadow(false);
	RootComponent = Mesh;

	HoverParams.Width = 22.f;
	HoverParams.Lift = 14.f;
}

void AHexOverlay::Build(const FHexGrid& InGrid, const FTerrainHeight& InHeight)
{
	Grid = InGrid;
	Height = InHeight;
	Hover.Reset();

	if (!Material)
	{
		Material = Materials::MakeUnlitVertexColor(this);
	}

	const FMeshData Lines = MeshBuilders::BuildHexEdges(Grid, Height, LineParams, LineColor);
	Mesh->CreateMeshSection_LinearColor(LinesSection, Lines.Vertices, Lines.Triangles, Lines.Normals, Lines.UVs,
		Lines.Colors, TArray<FProcMeshTangent>(), /*bCreateCollision=*/ false);
	Mesh->SetMaterial(LinesSection, Material);
	Mesh->ClearMeshSection(HoverSection);
	UE_LOG(LogMuraBito, Log, TEXT("HexOverlay: %d tiles, %d line vertices"), Grid.NumTiles(), Lines.Vertices.Num());
}

void AHexOverlay::SetHover(TOptional<FHex> Hex)
{
	if (Hex == Hover)
	{
		return;
	}
	Hover = Hex;
	if (!Hover.IsSet())
	{
		Mesh->ClearMeshSection(HoverSection);
		return;
	}
	const FMeshData Outline = MeshBuilders::BuildHexOutline(Grid, Hover.GetValue(), Height, HoverParams, HoverColor);
	Mesh->CreateMeshSection_LinearColor(HoverSection, Outline.Vertices, Outline.Triangles, Outline.Normals, Outline.UVs,
		Outline.Colors, TArray<FProcMeshTangent>(), /*bCreateCollision=*/ false);
	Mesh->SetMaterial(HoverSection, Material);
}
```

- [ ] **Step 4: Build and run the full suite**

Run: `$EXP/scripts/test.sh`
Expected: the build compiles with no errors, and all `MuraBito.*` tests pass (18 tests from Tasks 2–5).

If UHT reports a class-name clash (for example with an engine type called `ATerrain`), rename the clashing class to another plain name, such as `AGround`. Update every reference, and say so in the commit message.

- [ ] **Step 5: Commit**

```bash
W=/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04
git -C $W rev-parse --abbrev-ref HEAD   # must print worktree-exp-04
git -C $W add -A Experiments/exp-04/Source
git -C $W commit -m "exp-04: ATerrain and AHexOverlay actors with runtime-built materials

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: `ACameraRig`, `AInputController` and `AWorldBuilder`: the playable world

**Files:**
- Create: `$EXP/Source/MuraBito/Public/CameraRig.h`, `$EXP/Source/MuraBito/Private/CameraRig.cpp`
- Create: `$EXP/Source/MuraBito/Public/InputController.h`, `$EXP/Source/MuraBito/Private/InputController.cpp`
- Create: `$EXP/Source/MuraBito/Public/WorldBuilder.h`, `$EXP/Source/MuraBito/Private/WorldBuilder.cpp`

**Interfaces:**
- Consumes: `CameraMath::*`, `FZoomRange`, `ATerrain`, `AHexOverlay`, `FHexGrid`, `FTerrainHeight`, `LogMuraBito`.
- Produces:
  - `ACameraRig : APawn { void Configure(const FBox2D& Bounds, float BaseZ); void AddPan(const FVector2D& ScreenDir); void AddPanWorld(const FVector2D& WorldDelta); void AddZoom(float Steps); float GetArmLength() const; }`. `AddZoom(+)` zooms out.
  - `AInputController : APlayerController { void SetWorldRefs(ATerrain*, AHexOverlay*); }`
  - `AWorldBuilder : AGameModeBase`. It's the global default game mode (`/Script/MuraBito.WorldBuilder`, already set in `DefaultEngine.ini` in Task 1).

- [ ] **Step 1: Write `ACameraRig`**

`Source/MuraBito/Public/CameraRig.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "CameraMath.h"
#include "GameFramework/Pawn.h"
#include "CameraRig.generated.h"

class UCameraComponent;
class USpringArmComponent;

/**
 * Overhead camera: pans over the map's XY bounds and zooms along a spring arm.
 * Tilt follows zoom, steep when far and oblique when close. No yaw rotation.
 * (Subclasses APawn only because the engine possesses pawns.)
 */
UCLASS()
class MURABITO_API ACameraRig : public APawn
{
	GENERATED_BODY()

public:
	ACameraRig();

	virtual void Tick(float DeltaSeconds) override;

	/** Pan limits (XY) and the fixed height of the pivot. */
	void Configure(const FBox2D& InBounds, float InBaseZ);

	/** Screen-relative pan direction for this frame: X right, Y up-screen, each in [-1, 1]. */
	void AddPan(const FVector2D& ScreenDir);

	/** Direct world XY offset for this frame (mouse drag). */
	void AddPanWorld(const FVector2D& WorldDelta);

	/** Wheel steps: positive zooms out. */
	void AddZoom(float Steps);

	float GetArmLength() const;

	UPROPERTY(EditAnywhere, Category = "Camera") float NearArm = 1500.f;
	UPROPERTY(EditAnywhere, Category = "Camera") float FarArm = 12000.f;
	UPROPERTY(EditAnywhere, Category = "Camera") float NearPitch = -45.f;
	UPROPERTY(EditAnywhere, Category = "Camera") float FarPitch = -75.f;
	/** cm/s at the near limit; scales with arm length. */
	UPROPERTY(EditAnywhere, Category = "Camera") float PanSpeed = 1500.f;
	/** Fraction of the zoom range per wheel step. */
	UPROPERTY(EditAnywhere, Category = "Camera") float ZoomStep = 0.08f;
	UPROPERTY(EditAnywhere, Category = "Camera") float ZoomSmoothing = 10.f;

	UPROPERTY(VisibleAnywhere, Category = "Camera") TObjectPtr<USceneComponent> Pivot;
	UPROPERTY(VisibleAnywhere, Category = "Camera") TObjectPtr<USpringArmComponent> Arm;
	UPROPERTY(VisibleAnywhere, Category = "Camera") TObjectPtr<UCameraComponent> Camera;

private:
	FZoomRange ZoomRange() const;
	void ApplyZoom();

	FBox2D Bounds = FBox2D(FVector2D(-1.0e6), FVector2D(1.0e6));
	float BaseZ = 0.f;
	float Zoom01 = 0.6f;
	float TargetZoom01 = 0.6f;
	FVector2D PendingScreenPan = FVector2D::ZeroVector;
	FVector2D PendingWorldPan = FVector2D::ZeroVector;
};
```

`Source/MuraBito/Private/CameraRig.cpp`:

```cpp
#include "CameraRig.h"

#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"

ACameraRig::ACameraRig()
{
	PrimaryActorTick.bCanEverTick = true;

	Pivot = CreateDefaultSubobject<USceneComponent>(TEXT("Pivot"));
	RootComponent = Pivot;

	Arm = CreateDefaultSubobject<USpringArmComponent>(TEXT("Arm"));
	Arm->SetupAttachment(Pivot);
	Arm->bDoCollisionTest = false;
	Arm->bEnableCameraLag = false;
	Arm->bUsePawnControlRotation = false;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Arm, USpringArmComponent::SocketName);

	ApplyZoom();
}

FZoomRange ACameraRig::ZoomRange() const
{
	FZoomRange Range;
	Range.NearArm = NearArm;
	Range.FarArm = FarArm;
	Range.NearPitch = NearPitch;
	Range.FarPitch = FarPitch;
	return Range;
}

void ACameraRig::ApplyZoom()
{
	const FZoomRange Range = ZoomRange();
	Arm->TargetArmLength = CameraMath::ArmLength(Range, Zoom01);
	Arm->SetRelativeRotation(FRotator(CameraMath::Pitch(Range, Zoom01), 0.f, 0.f));
}

void ACameraRig::Configure(const FBox2D& InBounds, float InBaseZ)
{
	Bounds = InBounds;
	BaseZ = InBaseZ;
	const FVector2D Clamped = CameraMath::ClampToBounds(FVector2D(GetActorLocation()), Bounds);
	SetActorLocation(FVector(Clamped.X, Clamped.Y, BaseZ));
}

void ACameraRig::AddPan(const FVector2D& ScreenDir) { PendingScreenPan += ScreenDir; }
void ACameraRig::AddPanWorld(const FVector2D& WorldDelta) { PendingWorldPan += WorldDelta; }

void ACameraRig::AddZoom(float Steps)
{
	TargetZoom01 = FMath::Clamp(TargetZoom01 + Steps * ZoomStep, 0.f, 1.f);
}

float ACameraRig::GetArmLength() const { return Arm->TargetArmLength; }

void ACameraRig::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	Zoom01 = FMath::FInterpTo(Zoom01, TargetZoom01, DeltaSeconds, ZoomSmoothing);
	ApplyZoom();

	const float Speed = CameraMath::PanSpeed(PanSpeed, ZoomRange(), Zoom01);
	const FVector2D Move = CameraMath::ScreenDirToWorld(PendingScreenPan.GetClampedToMaxSize(1.0)) * Speed * DeltaSeconds
		+ PendingWorldPan;
	PendingScreenPan = FVector2D::ZeroVector;
	PendingWorldPan = FVector2D::ZeroVector;

	const FVector2D Next = CameraMath::ClampToBounds(FVector2D(GetActorLocation()) + Move, Bounds);
	SetActorLocation(FVector(Next.X, Next.Y, BaseZ));
}
```

- [ ] **Step 2: Write `AInputController`**

`Source/MuraBito/Public/InputController.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "InputController.generated.h"

class AHexOverlay;
class ATerrain;
class ACameraRig;
class UInputAction;
class UInputMappingContext;
struct FInputActionValue;

/**
 * Keyboard/mouse input for the camera rig, plus picking the hex under the cursor.
 * Input actions and the mapping context are created in code, not as assets.
 */
UCLASS()
class MURABITO_API AInputController : public APlayerController
{
	GENERATED_BODY()

public:
	AInputController();

	void SetWorldRefs(ATerrain* InTerrain, AHexOverlay* InOverlay);

	/** Pixels from the viewport edge that start edge scrolling. */
	UPROPERTY(EditAnywhere, Category = "Input") float EdgeScrollMargin = 8.f;
	/** Drag pan: world cm per pixel, per cm of arm length. */
	UPROPERTY(EditAnywhere, Category = "Input") float DragCmPerPixelPerArm = 0.0012f;

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;
	virtual void PlayerTick(float DeltaTime) override;

private:
	void CreateInputObjects();
	void OnMove(const FInputActionValue& Value);
	void OnZoom(const FInputActionValue& Value);
	void UpdateEdgeScroll();
	void UpdateDrag();
	void UpdateHover();
	ACameraRig* Rig() const;

	UPROPERTY() TObjectPtr<UInputMappingContext> Context;
	UPROPERTY() TObjectPtr<UInputAction> MoveAction;
	UPROPERTY() TObjectPtr<UInputAction> ZoomAction;

	TWeakObjectPtr<ATerrain> Terrain;
	TWeakObjectPtr<AHexOverlay> Overlay;

	bool bDragging = false;
	FVector2D LastMouse = FVector2D::ZeroVector;
};
```

`Source/MuraBito/Private/InputController.cpp`:

```cpp
#include "InputController.h"

#include "CameraMath.h"
#include "CameraRig.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "HexOverlay.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Terrain.h"

AInputController::AInputController()
{
	bShowMouseCursor = true;
	bEnableClickEvents = false;
	bEnableMouseOverEvents = false;
}

void AInputController::SetWorldRefs(ATerrain* InTerrain, AHexOverlay* InOverlay)
{
	Terrain = InTerrain;
	Overlay = InOverlay;
}

ACameraRig* AInputController::Rig() const
{
	return Cast<ACameraRig>(GetPawn());
}

void AInputController::CreateInputObjects()
{
	if (Context)
	{
		return;
	}
	MoveAction = NewObject<UInputAction>(this, TEXT("Move"));
	MoveAction->ValueType = EInputActionValueType::Axis2D;
	ZoomAction = NewObject<UInputAction>(this, TEXT("Zoom"));
	ZoomAction->ValueType = EInputActionValueType::Axis1D;

	Context = NewObject<UInputMappingContext>(this, TEXT("CameraControls"));

	// Move is (X right, Y up-screen). Keys give +X by default; Swizzle moves the value to Y; Negate flips it.
	auto MapMove = [this](const FKey& Key, bool bToY, bool bNegate)
	{
		FEnhancedActionKeyMapping& Mapping = Context->MapKey(MoveAction, Key);
		if (bToY)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierSwizzleAxis>(this)); // default order YXZ
		}
		if (bNegate)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierNegate>(this));
		}
	};
	MapMove(EKeys::D, false, false);
	MapMove(EKeys::A, false, true);
	MapMove(EKeys::W, true, false);
	MapMove(EKeys::S, true, true);
	MapMove(EKeys::Right, false, false);
	MapMove(EKeys::Left, false, true);
	MapMove(EKeys::Up, true, false);
	MapMove(EKeys::Down, true, true);

	Context->MapKey(ZoomAction, EKeys::MouseWheelAxis);
}

void AInputController::SetupInputComponent()
{
	Super::SetupInputComponent();
	CreateInputObjects();

	UEnhancedInputComponent* Input = CastChecked<UEnhancedInputComponent>(InputComponent);
	Input->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AInputController::OnMove);
	Input->BindAction(ZoomAction, ETriggerEvent::Triggered, this, &AInputController::OnZoom);
}

void AInputController::BeginPlay()
{
	Super::BeginPlay();
	CreateInputObjects();
	if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
	{
		Subsystem->AddMappingContext(Context, 0);
	}

	FInputModeGameAndUI Mode;
	Mode.SetHideCursorDuringCapture(false);
	Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	SetInputMode(Mode);
}

void AInputController::OnMove(const FInputActionValue& Value)
{
	if (ACameraRig* R = Rig())
	{
		R->AddPan(Value.Get<FVector2D>());
	}
}

void AInputController::OnZoom(const FInputActionValue& Value)
{
	if (ACameraRig* R = Rig())
	{
		// Wheel up is positive and should zoom in.
		R->AddZoom(-Value.Get<float>());
	}
}

void AInputController::PlayerTick(float DeltaTime)
{
	Super::PlayerTick(DeltaTime);
	UpdateEdgeScroll();
	UpdateDrag();
	UpdateHover();
}

void AInputController::UpdateEdgeScroll()
{
	ACameraRig* R = Rig();
	float MouseX, MouseY;
	if (!R || bDragging || !GetMousePosition(MouseX, MouseY))
	{
		return;
	}
	int32 SizeX, SizeY;
	GetViewportSize(SizeX, SizeY);
	FVector2D Dir = FVector2D::ZeroVector;
	if (MouseX <= EdgeScrollMargin) Dir.X -= 1.0;
	if (MouseX >= SizeX - 1 - EdgeScrollMargin) Dir.X += 1.0;
	if (MouseY <= EdgeScrollMargin) Dir.Y += 1.0;
	if (MouseY >= SizeY - 1 - EdgeScrollMargin) Dir.Y -= 1.0;
	if (!Dir.IsZero())
	{
		R->AddPan(Dir);
	}
}

void AInputController::UpdateDrag()
{
	ACameraRig* R = Rig();
	float MouseX, MouseY;
	const bool bHaveMouse = GetMousePosition(MouseX, MouseY);
	const bool bDown = IsInputKeyDown(EKeys::MiddleMouseButton);
	if (!R || !bHaveMouse || !bDown)
	{
		bDragging = false;
		return;
	}
	const FVector2D Mouse(MouseX, MouseY);
	if (bDragging)
	{
		const float CmPerPixel = DragCmPerPixelPerArm * R->GetArmLength();
		R->AddPanWorld(CameraMath::DragToWorld(Mouse - LastMouse, CmPerPixel));
	}
	bDragging = true;
	LastMouse = Mouse;
}

void AInputController::UpdateHover()
{
	if (!Overlay.IsValid())
	{
		return;
	}
	TOptional<FHex> Tile;
	FHitResult Hit;
	if (Terrain.IsValid() && GetHitResultUnderCursor(ECC_Visibility, false, Hit) && Hit.GetActor() == Terrain.Get())
	{
		const FHexGrid& Grid = Overlay->GetGrid();
		const FHex Hex = Grid.XYToHex(FVector2D(Hit.ImpactPoint));
		if (Grid.Contains(Hex))
		{
			Tile = Hex;
		}
	}
	Overlay->SetHover(Tile);
}
```

- [ ] **Step 3: Write `AWorldBuilder`**

`Source/MuraBito/Public/WorldBuilder.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "HexGrid.h"
#include "TerrainHeight.h"
#include "WorldBuilder.generated.h"

class AHexOverlay;
class ATerrain;

/**
 * Builds the whole world at startup, since the project has no level asset: terrain, hex overlay,
 * lighting and sky, and the player's camera rig. Reads -Seed=N from the command line (default 0).
 */
UCLASS()
class MURABITO_API AWorldBuilder : public AGameModeBase
{
	GENERATED_BODY()

public:
	AWorldBuilder();

	virtual void BeginPlay() override;

	/** Spawns our camera rig for the player instead of looking for a PlayerStart (the map has none). */
	virtual void RestartPlayer(AController* NewPlayer) override;

	UPROPERTY(EditAnywhere, Category = "World") float TileSize = 300.f;
	UPROPERTY(EditAnywhere, Category = "World") int32 MapRadius = 12;
	UPROPERTY(EditAnywhere, Category = "World") float TerrainSpacing = 50.f;

private:
	static int32 ReadSeed();
	void SpawnLighting();
	void SetUpPlayer(APlayerController* Player);
	float AverageTileHeight() const;

	FHexGrid Grid;
	FTerrainHeight Height;
	bool bBuilt = false;

	UPROPERTY() TObjectPtr<ATerrain> Terrain;
	UPROPERTY() TObjectPtr<AHexOverlay> Overlay;
};
```

`Source/MuraBito/Private/WorldBuilder.cpp`:

```cpp
#include "WorldBuilder.h"

#include "CameraRig.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/SkyLight.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HexOverlay.h"
#include "InputController.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "MuraBitoLog.h"
#include "Terrain.h"

AWorldBuilder::AWorldBuilder()
{
	DefaultPawnClass = ACameraRig::StaticClass();
	PlayerControllerClass = AInputController::StaticClass();
}

int32 AWorldBuilder::ReadSeed()
{
	FString Value;
	if (!FParse::Value(FCommandLine::Get(), TEXT("Seed="), Value))
	{
		UE_LOG(LogMuraBito, Log, TEXT("WorldBuilder: no -Seed given, using 0"));
		return 0;
	}
	if (!Value.IsNumeric())
	{
		UE_LOG(LogMuraBito, Warning, TEXT("WorldBuilder: -Seed=%s is not a number, using 0"), *Value);
		return 0;
	}
	return FCString::Atoi(*Value);
}

void AWorldBuilder::BeginPlay()
{
	Super::BeginPlay();

	const int32 Seed = ReadSeed();
	Grid = FHexGrid(TileSize, MapRadius);
	Height = FTerrainHeight(Seed);

	const FBox2D MapBounds = Grid.Bounds();
	const FBox2D TerrainArea = MapBounds.ExpandBy(2.0 * TileSize);

	Terrain = GetWorld()->SpawnActor<ATerrain>();
	Terrain->Build(Height, TerrainArea, TerrainSpacing);

	Overlay = GetWorld()->SpawnActor<AHexOverlay>();
	Overlay->Build(Grid, Height);

	SpawnLighting();
	bBuilt = true;

	UE_LOG(LogMuraBito, Log, TEXT("WorldBuilder: seed %d, %d tiles, tile size %.0f cm"), Seed, Grid.NumTiles(), TileSize);

	for (FConstPlayerControllerIterator It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
	{
		SetUpPlayer(It->Get());
	}
}

void AWorldBuilder::RestartPlayer(AController* NewPlayer)
{
	if (APlayerController* Player = Cast<APlayerController>(NewPlayer))
	{
		SetUpPlayer(Player);
	}
}

void AWorldBuilder::SetUpPlayer(APlayerController* Player)
{
	if (!Player)
	{
		return;
	}
	ACameraRig* Rig = Cast<ACameraRig>(Player->GetPawn());
	if (!Rig)
	{
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		Rig = GetWorld()->SpawnActor<ACameraRig>(FVector::ZeroVector, FRotator::ZeroRotator, Params);
		Player->Possess(Rig);
	}
	if (bBuilt)
	{
		Rig->Configure(Grid.Bounds(), AverageTileHeight());
		if (AInputController* Input = Cast<AInputController>(Player))
		{
			Input->SetWorldRefs(Terrain, Overlay);
		}
	}
}

float AWorldBuilder::AverageTileHeight() const
{
	double Sum = 0.0;
	const TArray<FHex> Tiles = Grid.Tiles();
	for (const FHex& Hex : Tiles)
	{
		const FVector2D P = Grid.HexToXY(Hex);
		Sum += Height.Height(P.X, P.Y);
	}
	return Tiles.Num() > 0 ? static_cast<float>(Sum / Tiles.Num()) : 0.f;
}

void AWorldBuilder::SpawnLighting()
{
	UWorld* World = GetWorld();

	ADirectionalLight* Sun = World->SpawnActor<ADirectionalLight>(FVector(0, 0, 2000), FRotator(-40.f, 35.f, 0.f));
	if (UDirectionalLightComponent* SunLight = Cast<UDirectionalLightComponent>(Sun->GetLightComponent()))
	{
		SunLight->SetMobility(EComponentMobility::Movable);
		SunLight->SetAtmosphereSunLight(true);
	}

	World->SpawnActor<ASkyAtmosphere>();

	ASkyLight* Sky = World->SpawnActor<ASkyLight>();
	if (USkyLightComponent* SkyLight = Sky->GetLightComponent())
	{
		SkyLight->SetMobility(EComponentMobility::Movable);
		SkyLight->SetRealTimeCapture(true);
		SkyLight->RecaptureSky();
	}

	World->SpawnActor<AExponentialHeightFog>();
}
```

If a light API doesn't compile, check the header under `$UE_ROOT/Engine/Source/Runtime/Engine/Classes/` (for example `Components/SkyLightComponent.h` has `SetRealTimeCapture(bool)` at 5.8.2) and adapt. Keep the same result: a movable sun used as the atmosphere sun, a real-time-capture sky light, sky atmosphere and height fog.

- [ ] **Step 4: Build and run the full suite**

Run: `$EXP/scripts/test.sh`
Expected: it compiles, and all `MuraBito.*` tests pass.

- [ ] **Step 5: Smoke-run the game offscreen and check the log**

Run it offscreen for a bounded time, so no window appears on the user's desktop:

```bash
cd /home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04/Experiments/exp-04 && \
timeout 180 ./scripts/game.sh -RenderOffscreen -unattended -Seed=7 > Saved/game-smoke.log 2>&1; \
rg --no-line-number "LogMuraBito|Error:|Fatal|Ensure condition failed" Saved/game-smoke.log
```

Expected lines:
- `LogMuraBito: WorldBuilder: seed 7, 469 tiles, tile size 300 cm`
- `LogMuraBito: Terrain: … vertices`
- `LogMuraBito: HexOverlay: 469 tiles, … line vertices`

There should be no `Fatal` or `Ensure condition failed`, and no errors from `LogMuraBito`. The first run may spend most of its time compiling shaders. That's fine as long as the `LogMuraBito` lines appear. A `timeout` exit (124) is expected, because the game keeps running until it's killed.

If the `WorldBuilder` line is missing, the game mode wasn't used. Check the log for which GameMode loaded. If `/Engine/Maps/Entry` overrides it, pass `?game=/Script/MuraBito.WorldBuilder` in the map URL in `game.sh` (`"$EDITOR" "$PROJECT" "/Engine/Maps/Entry?game=/Script/MuraBito.WorldBuilder" -game …`), and note it in the commit.

- [ ] **Step 6: Commit**

```bash
W=/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04
git -C $W rev-parse --abbrev-ref HEAD   # must print worktree-exp-04
git -C $W status --porcelain            # nothing under Saved/ or Binaries/ may appear
git -C $W add -A Experiments/exp-04/Source Experiments/exp-04/scripts
git -C $W commit -m "exp-04: camera rig, input controller and world builder make the world playable

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 7: Hand check (controller asks the user)**

The user runs `Experiments/exp-04/scripts/game.sh` (or opens the editor with `editor.sh` and presses Play) and confirms:
- hilly green-to-rock terrain with dark hex lines that follow the hills,
- WASD/arrows, screen edges and middle-drag pan the view, which stops at the map edges,
- the wheel zooms, and the view tilts steeper as it zooms out,
- a yellow outline follows the tile under the cursor, including on slopes.

Tuning changes from this check (speeds, colors, ranges) are small follow-up commits.

---

### Task 8: Manifest entry

**Files:**
- Modify: `/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04/Experiments/manifest.md` (append at the end)

- [ ] **Step 1: Append the exp-04 entry**

Add this after the exp-03 entry, with a `---` separator line before it, as between the other entries:

```markdown
## exp-04 — UE5 hex terrain and camera

- **Started:** 2026-09-18
- **Stack:** Unreal Engine 5.8.2, C++ (Linux). Set `UE_ROOT` to use another engine install.
- **Build:** `Experiments/exp-04/scripts/build.sh`
- **Run:** `Experiments/exp-04/scripts/game.sh [-Seed=N]`, or `scripts/editor.sh` and press Play
- **Test:** `Experiments/exp-04/scripts/test.sh [TestPathPrefix]` (headless UE automation tests)
- **Design:** [`exp-04/docs/specs/2026-09-18-exp-04-ue5-hex-terrain-design.md`](exp-04/docs/specs/2026-09-18-exp-04-ue5-hex-terrain-design.md)

### Why

A separate line from exp-00–03. Instead of mocking AI in pygame, this gets a basic Unreal Engine 5 world running.

### What

A C++ UE5 project with no binary assets. At startup the game mode builds everything into the engine's empty `/Engine/Maps/Entry` map:

- **Terrain.** Hilly ground made from seeded layered noise (`-Seed=N`).
- **Hex grid.** A pointy-top hex grid, radius 12, defined on a flat 2D plane and draped onto the terrain as thin lines. A 2D hex coordinate stands for a spot in the 3D world.
- **Camera.** An overhead camera that pans (WASD/arrows, screen edges, middle-drag) and zooms (wheel). It tilts from about 75° down far out to about 45° close in.
- **Hover.** An outline on the tile under the mouse.

The repo holds only what's needed to build and run: no engine code, and no `.uasset`/`.umap` files. Don't save the Entry map from the editor.

### Layout

- `MuraBito.uproject`, `Config/`: project file and settings (default map, game mode, Enhanced Input)
- `Source/MuraBito/`: `HexGrid`, `TerrainHeight`, `MeshBuilders`, `CameraMath` (pure math); `Terrain`, `HexOverlay`, `CameraRig`, `InputController`, `WorldBuilder` (actors); `Materials` (runtime materials)
- `Source/MuraBito/Private/Tests/`: automation tests for the hex grid, height function, mesh builders and camera math
- `scripts/`: build, editor, game and test wrappers around the local engine install

### Controls

WASD/arrows or screen edges pan · middle-drag pans · wheel zooms · mouse hover highlights a tile.
```

- [ ] **Step 2: Commit**

```bash
W=/home/lexa/DevProjects/_GameDev/MuraBito/.claude/worktrees/exp-04
git -C $W rev-parse --abbrev-ref HEAD   # must print worktree-exp-04
git -C $W add Experiments/manifest.md
git -C $W commit -m "exp-04: manifest entry

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```
