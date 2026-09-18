#include "CameraMath.h"

namespace CameraMath
{
	float ArmLength(const FZoomRange& Range, float Zoom01)
	{
		return FMath::Lerp(Range.NearArm, Range.FarArm, FMath::Clamp(Zoom01, 0.f, 1.f));
	}

	float Pitch(const FZoomRange& Range, float Zoom01)
	{
		return FMath::Lerp(Range.NearPitch, Range.FarPitch, FMath::Clamp(Zoom01, 0.f, 1.f));
	}

	FVector2D ClampToBounds(const FVector2D& Point, const FBox2D& Bounds)
	{
		return FVector2D(
			FMath::Clamp(Point.X, Bounds.Min.X, Bounds.Max.X),
			FMath::Clamp(Point.Y, Bounds.Min.Y, Bounds.Max.Y));
	}

	FVector2D ScreenDirToWorld(const FVector2D& ScreenDir)
	{
		return FVector2D(ScreenDir.Y, ScreenDir.X);
	}

	FVector2D DragToWorld(const FVector2D& PixelDelta, float CmPerPixel)
	{
		return FVector2D(PixelDelta.Y * CmPerPixel, -PixelDelta.X * CmPerPixel);
	}

	float PanSpeed(float BaseSpeed, const FZoomRange& Range, float Zoom01)
	{
		return BaseSpeed * ArmLength(Range, Zoom01) / Range.NearArm;
	}
}
