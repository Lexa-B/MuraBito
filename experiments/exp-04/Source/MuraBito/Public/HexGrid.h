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
