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
