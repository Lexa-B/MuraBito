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
