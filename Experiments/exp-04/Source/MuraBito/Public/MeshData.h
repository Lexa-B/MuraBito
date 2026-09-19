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
