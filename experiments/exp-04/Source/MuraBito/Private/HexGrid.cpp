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
