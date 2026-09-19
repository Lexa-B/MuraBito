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
