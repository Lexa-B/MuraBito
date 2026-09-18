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
