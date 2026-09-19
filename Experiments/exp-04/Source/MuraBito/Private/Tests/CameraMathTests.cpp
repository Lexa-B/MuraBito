#include "Misc/AutomationTest.h"
#include "CameraMath.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	constexpr EAutomationTestFlags CameraTestFlags =
		EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::EngineFilter;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCameraZoomTiltTest, "MuraBito.CameraMath.ZoomTilt", CameraTestFlags)
bool FCameraZoomTiltTest::RunTest(const FString& Parameters)
{
	const FZoomRange Z;
	TestEqual(TEXT("near arm"), CameraMath::ArmLength(Z, 0.f), 1500.f, 0.01f);
	TestEqual(TEXT("far arm"), CameraMath::ArmLength(Z, 1.f), 12000.f, 0.01f);
	TestEqual(TEXT("mid arm"), CameraMath::ArmLength(Z, 0.5f), 6750.f, 0.01f);
	TestEqual(TEXT("near pitch is oblique"), CameraMath::Pitch(Z, 0.f), -45.f, 0.01f);
	TestEqual(TEXT("far pitch is steep"), CameraMath::Pitch(Z, 1.f), -75.f, 0.01f);
	TestEqual(TEXT("mid pitch"), CameraMath::Pitch(Z, 0.5f), -60.f, 0.01f);
	TestEqual(TEXT("zoom clamps low"), CameraMath::ArmLength(Z, -1.f), 1500.f, 0.01f);
	TestEqual(TEXT("zoom clamps high"), CameraMath::Pitch(Z, 2.f), -75.f, 0.01f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCameraClampTest, "MuraBito.CameraMath.Clamp", CameraTestFlags)
bool FCameraClampTest::RunTest(const FString& Parameters)
{
	const FBox2D B(FVector2D(-100, -50), FVector2D(100, 50));
	TestTrue(TEXT("inside unchanged"), CameraMath::ClampToBounds(FVector2D(10, 20), B).Equals(FVector2D(10, 20)));
	TestTrue(TEXT("clamped max"), CameraMath::ClampToBounds(FVector2D(500, 500), B).Equals(FVector2D(100, 50)));
	TestTrue(TEXT("clamped min"), CameraMath::ClampToBounds(FVector2D(-500, -500), B).Equals(FVector2D(-100, -50)));
	TestTrue(TEXT("clamped one axis"), CameraMath::ClampToBounds(FVector2D(0, 99), B).Equals(FVector2D(0, 50)));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCameraPanMappingTest, "MuraBito.CameraMath.PanMapping", CameraTestFlags)
bool FCameraPanMappingTest::RunTest(const FString& Parameters)
{
	// Screen up -> world forward (+X); screen right -> world right (+Y).
	TestTrue(TEXT("up is forward"), CameraMath::ScreenDirToWorld(FVector2D(0, 1)).Equals(FVector2D(1, 0)));
	TestTrue(TEXT("right is right"), CameraMath::ScreenDirToWorld(FVector2D(1, 0)).Equals(FVector2D(0, 1)));

	// Dragging moves the ground with the cursor: the mouse moves right (+px X), so the camera moves left (-Y);
	// the mouse moves down (+px Y, screen coords), so the camera moves forward (+X).
	TestTrue(TEXT("drag right"), CameraMath::DragToWorld(FVector2D(10, 0), 2.f).Equals(FVector2D(0, -20)));
	TestTrue(TEXT("drag down"), CameraMath::DragToWorld(FVector2D(0, 10), 2.f).Equals(FVector2D(20, 0)));

	// Pan speed scales with arm length: twice as fast at twice the distance.
	const FZoomRange Z;
	TestEqual(TEXT("near speed is base"), CameraMath::PanSpeed(1000.f, Z, 0.f), 1000.f, 0.01f);
	TestEqual(TEXT("far speed scales"), CameraMath::PanSpeed(1000.f, Z, 1.f), 8000.f, 0.01f);
	return true;
}

#endif
