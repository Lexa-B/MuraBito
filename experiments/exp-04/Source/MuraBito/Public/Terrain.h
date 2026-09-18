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
