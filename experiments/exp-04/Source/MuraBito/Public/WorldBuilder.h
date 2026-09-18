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
