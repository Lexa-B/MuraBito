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
	TestTrue(TEXT("mesh is not empty"), Mesh.Vertices.Num() > 0);
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
